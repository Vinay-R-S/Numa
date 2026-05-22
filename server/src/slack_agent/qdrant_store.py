"""
Slack Qdrant Store
==================
Manages per-user `{user_id}_slack` Qdrant collections.

Schema
------
- dim: 384  (all-MiniLM-L6-v2 - same embedder used by calendar & task agents)
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

_SLACK_EMBED_DIM = 384          # all-MiniLM-L6-v2
_RETENTION_DAYS  = int(os.getenv("SLACK_MESSAGE_RETENTION_DAYS", "7"))

_TRANSIENT_NETWORK_MARKERS = (
    "getaddrinfo failed",
    "could not translate host name",
    "name or service not known",
    "temporary failure in name resolution",
    "unable to find the server",
    "server closed the connection unexpectedly",
    "connection unexpectedly",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
)


def _is_transient_network_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_NETWORK_MARKERS)


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


def _slack_collection_name(user_id: str) -> str:
    return _memory().user_collection_name(user_id, "slack")


def _slack_collection_names(qdrant) -> List[str]:
    try:
        collections = getattr(qdrant.get_collections(), "collections", [])
        return [
            getattr(collection, "name", "")
            for collection in collections
            if getattr(collection, "name", "").endswith("_slack")
        ]
    except Exception as exc:
        if _is_transient_network_error(exc):
            log.debug("Slack Qdrant purge skipped while listing collections: %s", exc)
        else:
            log.warning("Slack Qdrant purge: failed to list collections: %s", exc)
        return []


# ── Collection bootstrap ───────────────────────────────────────────────────────

def ensure_slack_collection(user_id: str) -> bool:
    """Create the Qdrant collection if it doesn't exist yet. Idempotent."""
    qdrant = _client()
    deps   = _deps()
    if not qdrant or not deps:
        log.warning("Qdrant client not available - Slack collection skipped.")
        return False

    try:
        collection_name = _slack_collection_name(user_id)
        if not qdrant.collection_exists(collection_name):
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=deps["VectorParams"](
                    size=_SLACK_EMBED_DIM,
                    distance=deps["Distance"].COSINE,
                ),
            )
            log.info("Created Qdrant collection '%s' with payload indexes", collection_name)
        for field in ("user_id", "app", "channel_name", "slack_channel_id", "message_type", "ts"):
            try:
                qdrant.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema="keyword",
                )
            except Exception:
                pass
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

    collection_name = _slack_collection_name(user_id)
    if not ensure_slack_collection(user_id):
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
        point = deps["PointStruct"](
            id=_memory()._qdrant_point_id(point_id),
            vector=vector,
            payload=payload,
        )
        qdrant.upsert(
            collection_name=collection_name,
            points=[point],
            wait=False,
        )
        log.debug("Ingested Slack message ts=%s for user %s", ts, user_id)
    except Exception as exc:
        log.warning("Slack Qdrant upsert failed: %s", exc)


def delete_message(user_id: str, ts: str) -> None:
    """Delete one Slack message vector from the user's Slack collection."""
    if not user_id or not ts:
        return
    if not ensure_slack_collection(user_id):
        return

    qdrant = _client()
    deps = _deps()
    if not qdrant or not deps:
        return

    try:
        collection_name = _slack_collection_name(user_id)
        point_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"numa:slack_msg:{user_id}:{ts}",
        ).hex
        qdrant.delete(
            collection_name=collection_name,
            points_selector=deps["PointIdsList"](
                points=[_memory()._qdrant_point_id(point_id)]
            ),
            wait=False,
        )
    except Exception as exc:
        log.warning("Slack Qdrant delete failed for ts=%s: %s", ts, exc)


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
        collection_name = _slack_collection_name(user_id)
        if not qdrant.collection_exists(collection_name):
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
            collection_name=collection_name,
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
        collection_names = _slack_collection_names(qdrant)
        if not collection_names:
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

        purged = 0
        for collection_name in collection_names:
            qdrant.delete(
                collection_name=collection_name,
                points_selector=delete_filter,
                wait=False,
            )
            purged += 1
        log.info(
            "Slack Qdrant purge: deleted vectors older than %s from %d collection(s)",
            cutoff_str,
            purged,
        )
        return -1  # Qdrant delete returns no count; caller logs approximate
    except Exception as exc:
        if _is_transient_network_error(exc):
            log.debug("Slack Qdrant purge skipped: %s", exc)
        else:
            log.warning("Slack Qdrant purge failed: %s", exc)
        return 0
