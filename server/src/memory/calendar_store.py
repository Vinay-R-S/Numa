"""Calendar RAG - per-user Qdrant collections ("{user_id}_calendar").

NUMA-107 P3 (PLAN 16.5): extracted from the memory god-file. Uses the shared
``memory_service`` singleton (and its CachedEmbedder) so the Qdrant client and
embedding model are only created once. ``memory_service`` is imported lazily
inside functions to avoid a circular import with service.py.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


log = logging.getLogger(__name__)

_CALENDAR_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


def _cal_qdrant_client():
    """Return the same Qdrant Cloud client used by the memory service."""
    from .service import memory_service

    return memory_service._qdrant_client()


def _calendar_collection_name(user_id: str) -> str:
    from .service import memory_service

    return memory_service.user_collection_name(user_id, "calendar")


def _ensure_calendar_collection(user_id: str) -> bool:
    """
    Create the user's calendar Qdrant collection if it doesn't exist.
    Idempotent - safe to call on every ingest.
    """
    from .service import memory_service

    try:
        qdrant = _cal_qdrant_client()
        deps   = memory_service._deps()
        if not qdrant or not deps:
            return False

        collection_name = _calendar_collection_name(user_id)
        if not qdrant.collection_exists(collection_name):
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=deps["VectorParams"](
                    size=_CALENDAR_EMBEDDING_DIM,
                    distance=deps["Distance"].COSINE,
                ),
            )
            for field in ("user_id", "app", "month", "event_id", "calendar_id"):
                try:
                    qdrant.create_payload_index(
                        collection_name=collection_name,
                        field_name=field,
                        field_schema="keyword",
                    )
                except Exception:
                    pass
            log.info("Created Qdrant collection '%s' with payload indexes", collection_name)
        else:
            for field in ("user_id", "app", "month", "event_id", "calendar_id"):
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
        log.warning("_ensure_calendar_collection failed: %s", exc)
        return False


def store_calendar_event(
    user_id: str,
    user_email: str,
    calendar_id: str,
    event_id: str,
    title: str,
    description: Optional[str],
    start_at: datetime,
    end_at: datetime,
    is_all_day: bool,
    calendar_type: str = "personal",
) -> None:
    """
    Embed one Google Calendar event and upsert it into `{user_id}_calendar`.

    The point ID is stable - re-ingesting the same event updates the vector
    in place rather than creating a duplicate.
    """
    from .service import memory_service

    if not user_id or not event_id:
        return

    # Lazy import to avoid circular dependency
    try:
        from src.embedder import embedder  # type: ignore
    except ImportError:
        try:
            from ..embedder import embedder  # type: ignore
        except ImportError:
            log.warning("store_calendar_event: embedder not importable")
            return

    month_str = start_at.strftime("%Y-%m")
    text_for_embedding = (
        f"{title}. {description or ''}. "
        f"Start: {start_at.isoformat()}. End: {end_at.isoformat()}. "
        f"Calendar: {calendar_id}. Type: {calendar_type}."
    ).strip()

    vector = embedder.embed(text_for_embedding)
    if not vector:
        log.warning("store_calendar_event: embedding failed for event %s", event_id)
        return

    collection_name = _calendar_collection_name(user_id)
    if not _ensure_calendar_collection(user_id):
        return

    qdrant = _cal_qdrant_client()
    deps   = memory_service._deps()
    if not qdrant or not deps:
        return

    point_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"numa:cal_event:{user_id}:{calendar_id}:{event_id}",
    ).hex

    payload: Dict = {
        "user_id":       user_id,
        "user_email":    user_email,
        "app":           "google_calendar",
        "calendar_id":   calendar_id,
        "event_id":      event_id,
        "calendar_type": calendar_type,
        "title":         title,
        "description":   description or "",
        "start_at":      start_at.isoformat(),
        "end_at":        end_at.isoformat(),
        "is_all_day":    is_all_day,
        "month":         month_str,
        "text":          text_for_embedding,
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }

    try:
        point = deps["PointStruct"](
            id=memory_service._qdrant_point_id(point_id),
            vector=vector,
            payload=payload,
        )
        qdrant.upsert(
            collection_name=collection_name,
            points=[point],
            wait=False,
        )
    except Exception as exc:
        log.warning("store_calendar_event upsert failed: %s", exc)


def search_calendar_events(
    user_id: str,
    query: str,
    limit: int = 6,
) -> List[Dict]:
    """
    Semantic search over the user's calendar events stored in Qdrant.

    Returns a list of event dicts in order of relevance. Each dict has:
    title, start_at, end_at, description, calendar_id, is_all_day.
    """
    from .service import memory_service

    if not user_id or not query.strip():
        return []

    try:
        from src.embedder import embedder  # type: ignore
    except ImportError:
        try:
            from ..embedder import embedder  # type: ignore
        except ImportError:
            return []

    vector = embedder.embed(query.strip())
    if not vector:
        return []

    qdrant = _cal_qdrant_client()
    deps   = memory_service._deps()
    if not qdrant or not deps:
        return []

    try:
        collection_name = _calendar_collection_name(user_id)
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
                    match=deps["MatchValue"](value="google_calendar"),
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
            payload = getattr(hit, "payload", None) or {}
            results.append({
                "title":       payload.get("title", ""),
                "start_at":    payload.get("start_at", ""),
                "end_at":      payload.get("end_at", ""),
                "description": payload.get("description", ""),
                "calendar_id": payload.get("calendar_id", ""),
                "is_all_day":  payload.get("is_all_day", False),
                "calendar_type": payload.get("calendar_type", "personal"),
            })
        return results

    except Exception as exc:
        log.warning("search_calendar_events failed: %s", exc)
        return []


def delete_month_calendar_events(user_id: str, month_str: str) -> None:
    """
    Delete all Qdrant calendar vectors for *user_id* in *month_str* ("YYYY-MM").
    Called during monthly purge to keep the vector store in sync with Supabase.
    """
    from .service import memory_service

    if not user_id or not month_str:
        return

    _ensure_calendar_collection(user_id)

    qdrant = _cal_qdrant_client()
    deps   = memory_service._deps()
    if not qdrant or not deps:
        return

    try:
        collection_name = _calendar_collection_name(user_id)
        if not qdrant.collection_exists(collection_name):
            return

        month_filter = deps["Filter"](
            must=[
                deps["FieldCondition"](
                    key="user_id",
                    match=deps["MatchValue"](value=user_id),
                ),
                deps["FieldCondition"](
                    key="app",
                    match=deps["MatchValue"](value="google_calendar"),
                ),
                deps["FieldCondition"](
                    key="month",
                    match=deps["MatchValue"](value=month_str),
                ),
            ]
        )
        qdrant.delete(
            collection_name=collection_name,
            points_selector=month_filter,
            wait=False,
        )
        log.info(
            "Purged Qdrant calendar events for user %s month %s",
            user_id, month_str,
        )
    except Exception as exc:
        log.warning("delete_month_calendar_events failed: %s", exc)


def delete_calendar_event(user_id: str, event_id: str, calendar_id: Optional[str] = None) -> None:
    """
    Delete Qdrant calendar vectors for one Google Calendar event.
    Filters primarily by event_id so aliases like "primary" vs the user's
    email-backed primary calendar id do not leave stale vectors behind.
    """
    from .service import memory_service

    if not user_id or not event_id:
        return

    _ensure_calendar_collection(user_id)

    qdrant = _cal_qdrant_client()
    deps   = memory_service._deps()
    if not qdrant or not deps:
        return

    try:
        collection_name = _calendar_collection_name(user_id)
        if not qdrant.collection_exists(collection_name):
            return

        conditions = [
            deps["FieldCondition"](
                key="user_id",
                match=deps["MatchValue"](value=user_id),
            ),
            deps["FieldCondition"](
                key="app",
                match=deps["MatchValue"](value="google_calendar"),
            ),
            deps["FieldCondition"](
                key="event_id",
                match=deps["MatchValue"](value=event_id),
            ),
        ]
        if calendar_id and calendar_id != "primary":
            conditions.append(
                deps["FieldCondition"](
                    key="calendar_id",
                    match=deps["MatchValue"](value=calendar_id),
                )
            )

        qdrant.delete(
            collection_name=collection_name,
            points_selector=deps["Filter"](must=conditions),
            wait=False,
        )
    except Exception as exc:
        log.warning("delete_calendar_event failed: %s", exc)
