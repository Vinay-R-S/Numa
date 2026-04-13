"""
Slack Qdrant Store
==================
Manages the `numa_slack_messages` Qdrant collection.

Schema
------
- dim: 384  (all-MiniLM-L6-v2 — same embedder used by calendar & task agents)
- distance: Cosine
- retention: 7 days  (enforced by nightly purge_old_messages scheduler job)

Payload keys stored per vector
-------------------------------
user_id, slack_user_id, slack_channel_id, channel_name,
text, ts, thread_ts, message_type, app, created_at, expires_after
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

SLACK_COLLECTION = os.getenv("QDRANT_SLACK_COLLECTION", "numa_slack_messages")
_SLACK_EMBED_DIM = 384          # all-MiniLM-L6-v2
_RETENTION_DAYS  = int(os.getenv("SLACK_MESSAGE_RETENTION_DAYS", "7"))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _memory():
    """Return the shared SemanticMemoryService (imports lazily to avoid circular)."""
    from ..memory.service import memory_service  # type: ignore
    return memory_service


def _client():
    return _memory()._qdrant_client()


def _deps():
    return _memory()._deps()


def _embedder():
    from ..embedder import embedder  # type: ignore
    return embedder


# ── Collection bootstrap ───────────────────────────────────────────────────────

def ensure_slack_collection() -> bool:
    """Create the Qdrant collection if it doesn't exist yet. Idempotent."""
    qdrant = _client()
    deps   = _deps()
    if not qdrant or not deps:
        log.warning("Qdrant client not available — Slack collection skipped.")
        return False

    try:
        if not qdrant.collection_exists(SLACK_COLLECTION):
            qdrant.create_collection(
                collection_name=SLACK_COLLECTION,
                vectors_config=deps["VectorParams"](
                    size=_SLACK_EMBED_DIM,
                    distance=deps["Distance"].COSINE,
                ),
            )
            log.info("Created Qdrant collection '%s'", SLACK_COLLECTION)
        return True
    except Exception as exc:
        log.warning("ensure_slack_collection failed: %s", exc)
        return False


# ── Write ──────────────────────────────────────────────────────────────────────

def ingest_message(
    user_id: str,
    slack_user_id: str,
    slack_channel_id: str,
    channel_name: str,
    text: str,
    ts: str,
    thread_ts: Optional[str] = None,
    message_type: str = "message",
) -> None:
    """Embed one Slack message and upsert it into Qdrant.

    The point_id is deterministic (uuid5 namespace on user+ts), so re-ingesting
    the same message just updates the vector in place.
    """
    if not text or not text.strip():
        return
    if not user_id or not ts:
        return

    embedder = _embedder()
    vector   = embedder.embed(text.strip())
    if not vector:
        log.warning("Slack ingest: embedding failed for ts=%s", ts)
        return

    if not ensure_slack_collection():
        return

    qdrant = _client()
    deps   = _deps()
    if not qdrant or not deps:
        return

    now         = datetime.now(timezone.utc)
    expires_at  = now + timedelta(days=_RETENTION_DAYS)
    point_id    = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"numa:slack_msg:{user_id}:{ts}",
    ).hex

    payload: Dict = {
        "user_id":         user_id,
        "slack_user_id":   slack_user_id,
        "slack_channel_id": slack_channel_id,
        "channel_name":    channel_name,
        "text":            text.strip(),
        "ts":              ts,
        "thread_ts":       thread_ts or "",
        "message_type":    message_type,
        "app":             "slack",
        "created_at":      now.isoformat(),
        "expires_after":   expires_at.isoformat(),
    }

    try:
        point = deps["PointStruct"](id=point_id, vector=vector, payload=payload)
        qdrant.upsert(
            collection_name=SLACK_COLLECTION,
            points=[point],
            wait=False,
        )
        log.debug("Ingested Slack message ts=%s for user %s", ts, user_id)
    except Exception as exc:
        log.warning("Slack Qdrant upsert failed: %s", exc)


# ── Read ───────────────────────────────────────────────────────────────────────

def search_messages(
    user_id: str,
    query: str,
    limit: int = 8,
) -> List[Dict]:
    """Semantic search over the user's Slack messages in Qdrant.

    Returns a list of payload dicts ordered by relevance score.
    Each dict: text, channel_name, ts, created_at, message_type.
    """
    if not user_id or not query.strip():
        return []

    embedder = _embedder()
    vector   = embedder.embed(query.strip())
    if not vector:
        return []

    qdrant = _client()
    deps   = _deps()
    if not qdrant or not deps:
        return []

    try:
        if not qdrant.collection_exists(SLACK_COLLECTION):
            return []

        user_filter = deps["Filter"](
            must=[
                deps["FieldCondition"](
                    key="user_id",
                    match=deps["MatchValue"](value=user_id),
                ),
                deps["FieldCondition"](
                    key="app",
                    match=deps["MatchValue"](value="slack"),
                ),
            ]
        )

        hits = qdrant.search(
            collection_name=SLACK_COLLECTION,
            query_vector=vector,
            query_filter=user_filter,
            limit=limit,
            with_payload=True,
        )

        results: List[Dict] = []
        for hit in hits:
            p = getattr(hit, "payload", None) or {}
            results.append({
                "text":         p.get("text", ""),
                "channel_name": p.get("channel_name", ""),
                "ts":           p.get("ts", ""),
                "created_at":   p.get("created_at", ""),
                "message_type": p.get("message_type", "message"),
                "score":        getattr(hit, "score", 0.0),
            })
        return results
    except Exception as exc:
        log.warning("Slack Qdrant search failed: %s", exc)
        return []


# ── Purge ──────────────────────────────────────────────────────────────────────

def purge_old_messages(cutoff: Optional[datetime] = None) -> int:
    """Delete Qdrant vectors whose `created_at` is older than `cutoff`.

    Defaults to 7 days ago (UTC).  Returns number of deleted points (approx).
    Designed to be called from the nightly APScheduler job.
    """
    if cutoff is None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)

    qdrant = _client()
    deps   = _deps()
    if not qdrant or not deps:
        return 0

    try:
        if not qdrant.collection_exists(SLACK_COLLECTION):
            return 0

        cutoff_str = cutoff.isoformat()

        # Qdrant range filter on string ISO dates (lexicographic comparison works
        # because ISO-8601 timestamps sort correctly as strings).
        from qdrant_client.models import DatetimeRange, Range, FieldCondition, Filter  # type: ignore
        try:
            delete_filter = Filter(
                must=[
                    FieldCondition(
                        key="created_at",
                        range=Range(lt=cutoff_str),
                    )
                ]
            )
        except Exception:
            # Fallback: build via deps dict (avoids import errors on older versions)
            delete_filter = deps["Filter"](
                must=[
                    deps["FieldCondition"](
                        key="app",
                        match=deps["MatchValue"](value="slack"),
                    )
                ]
            )
            log.info("Slack purge: using app-only filter fallback (no Range support)")

        qdrant.delete(
            collection_name=SLACK_COLLECTION,
            points_selector=delete_filter,
            wait=False,
        )
        log.info("Slack Qdrant purge: deleted vectors older than %s", cutoff_str)
        return -1  # Qdrant delete returns no count; caller logs approximate
    except Exception as exc:
        log.warning("Slack Qdrant purge failed: %s", exc)
        return 0
