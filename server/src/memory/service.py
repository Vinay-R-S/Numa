"""Semantic memory service: generic memory, domain-text, and snapshot stores.

NUMA-107 P3 (PLAN 16.5): the former 1013-line god-file is split into three
cohesive modules. ``SemanticMemoryService`` keeps the store/search/delete
operations and subclasses ``MemoryClient`` (config + Qdrant client + embedding
bridge in client.py), so the ``memory_service`` singleton still exposes every
attribute and method callers rely on.

The per-user calendar RAG functions live in calendar_store.py and are re-exported
here so existing imports (``from ..memory.service import store_calendar_event``)
keep working.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .client import MemoryClient


log = logging.getLogger(__name__)


class SemanticMemoryService(MemoryClient):
    """Store and retrieve semantic memory: turns, snapshots, and domain text."""

    def _upsert_text_point(self, point_id: str, text: str, payload: dict, user_id: str) -> None:
        if not self.enabled:
            return
        collection_name = self.memory_collection_name(user_id)

        vector = self._embed(text)
        if not vector:
            return
        if not self._ensure_collection(collection_name=collection_name):
            return

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return

        try:
            point = deps["PointStruct"](
                id=self._qdrant_point_id(point_id),
                vector=vector,
                payload=payload,
            )
            qdrant.upsert(collection_name=collection_name, points=[point], wait=False)
        except Exception as exc:
            log.warning("Failed to upsert semantic memory point: %s", exc)

    def upsert_domain_text(
        self,
        *,
        user_id: str,
        domain: str,
        stable_key: str,
        text: str,
        payload: Optional[dict] = None,
    ) -> None:
        """Upsert one text document into a per-user domain collection."""
        if not self.enabled or not user_id or not domain or not stable_key or not text.strip():
            return

        vector = self._embed(text)
        if not vector:
            return

        collection_name = self.user_collection_name(user_id, domain)
        if not self._ensure_collection(collection_name=collection_name):
            return

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return

        point_id = self._stable_point_id(domain, user_id, stable_key)
        point_payload = {
            "user_id": user_id,
            "domain": domain,
            "stable_key": stable_key,
            "text": text.strip(),
            "source": f"{domain}_snapshot",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(payload or {}),
        }

        try:
            point = deps["PointStruct"](
                id=self._qdrant_point_id(point_id),
                vector=vector,
                payload=point_payload,
            )
            qdrant.upsert(collection_name=collection_name, points=[point], wait=False)
        except Exception as exc:
            log.warning("Failed to upsert %s domain point: %s", domain, exc)

    def delete_domain_point(self, *, user_id: str, domain: str, stable_key: str) -> None:
        if not self.enabled or not user_id or not domain or not stable_key:
            return

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return

        collection_name = self.user_collection_name(user_id, domain)
        try:
            if not qdrant.collection_exists(collection_name):
                return
            point_id = self._stable_point_id(domain, user_id, stable_key)
            qdrant.delete(
                collection_name=collection_name,
                points_selector=deps["PointIdsList"](
                    points=[self._qdrant_point_id(point_id)]
                ),
                wait=False,
            )
        except Exception as exc:
            log.warning("Failed to delete %s domain point: %s", domain, exc)

    def store_turn(self, user_id: str, query: str, response: str) -> None:
        if not self.enabled:
            return
        if not user_id:
            return

        content = f"User: {query.strip()}\nAssistant: {response.strip()}"
        payload = {
            "user_id": user_id,
            "text": content,
            "source": "calendar_agent",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._upsert_text_point(uuid.uuid4().hex, content, payload, user_id=user_id)

    def store_task_snapshot(
        self,
        user_id: str,
        task_id: str,
        title: str,
        status: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        source_name: Optional[str] = None,
        external_ref: Optional[str] = None,
    ) -> None:
        if not user_id or not task_id:
            return

        due_text = due_date.isoformat() if isinstance(due_date, datetime) else "none"
        source_label = source_name or "manual"
        description_text = (description or "").strip()

        text = (
            f"Task: {title.strip() or 'Untitled'}\n"
            f"Status: {status or 'planned'}\n"
            f"Due: {due_text}\n"
            f"Source: {source_label}\n"
            f"Details: {description_text or 'none'}"
        )

        payload = {
            "user_id": user_id,
            "text": text,
            "source": "task_snapshot",
            "task_id": task_id,
            "title": title,
            "status": status,
            "description": description_text,
            "due_date": due_text if due_text != "none" else None,
            "source_name": source_label,
            "external_ref": external_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        point_id = self._stable_point_id("task", user_id, task_id)
        self._upsert_text_point(point_id, text, payload, user_id=user_id)

    def store_calendar_event_snapshot(
        self,
        user_id: str,
        calendar_id: str,
        event_id: str,
        summary: str,
        start_at: datetime,
        end_at: datetime,
        status: str,
        description: Optional[str] = None,
    ) -> None:
        if not user_id or not calendar_id or not event_id:
            return

        description_text = (description or "").strip()
        text = (
            f"Calendar event: {summary.strip() or '(No title)'}\n"
            f"Calendar: {calendar_id}\n"
            f"Start: {start_at.isoformat()}\n"
            f"End: {end_at.isoformat()}\n"
            f"Status: {status or 'confirmed'}\n"
            f"Details: {description_text or 'none'}"
        )

        payload = {
            "user_id": user_id,
            "text": text,
            "source": "calendar_event_snapshot",
            "calendar_id": calendar_id,
            "event_id": event_id,
            "summary": summary,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "status": status,
            "description": description_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        stable_key = f"{calendar_id}:{event_id}"
        point_id = self._stable_point_id("calendar_event", user_id, stable_key)
        self._upsert_text_point(point_id, text, payload, user_id=user_id)

    def delete_snapshot(self, user_id: str, source: str, external_id: str) -> None:
        if not self.enabled:
            return
        if not user_id or not source or not external_id:
            return

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return

        point_id = self._stable_point_id(source, user_id, external_id)
        collection_name = self.memory_collection_name(user_id)
        try:
            if not qdrant.collection_exists(collection_name):
                return

            qdrant.delete(
                collection_name=collection_name,
                points_selector=deps["PointIdsList"](
                    points=[self._qdrant_point_id(point_id)]
                ),
                wait=False,
            )
        except Exception as exc:
            log.warning("Failed to delete semantic memory snapshot: %s", exc)

    def build_context_for_query(self, user_id: str, query: str) -> str:
        if not self.enabled:
            return ""
        if not user_id:
            return ""

        vector = self._embed(query.strip())
        if not vector:
            return ""
        collection_name = self.memory_collection_name(user_id)
        if not self._ensure_collection(collection_name=collection_name):
            return ""

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return ""

        try:
            user_filter = deps["Filter"](
                must=[
                    deps["FieldCondition"](
                        key="user_id",
                        match=deps["MatchValue"](value=user_id),
                    )
                ]
            )

            hits = qdrant.search(
                collection_name=collection_name,
                query_vector=vector,
                query_filter=user_filter,
                limit=self.context_limit,
                with_payload=True,
            )

            lines: List[str] = []
            for hit in hits:
                payload = getattr(hit, "payload", None) or {}
                text = str(payload.get("text", "")).strip()
                if text:
                    lines.append(f"- {text}")

            return "\n".join(lines)
        except Exception as exc:
            log.warning("Failed to retrieve semantic memory: %s", exc)
            return ""


memory_service = SemanticMemoryService()


# Calendar RAG functions live in calendar_store.py; re-exported so existing
# imports (``from ..memory.service import store_calendar_event``) keep working.
from .calendar_store import (  # noqa: E402
    _CALENDAR_EMBEDDING_DIM,
    _cal_qdrant_client,
    _calendar_collection_name,
    _ensure_calendar_collection,
    delete_calendar_event,
    delete_month_calendar_events,
    search_calendar_events,
    store_calendar_event,
)

__all__ = [
    "SemanticMemoryService",
    "memory_service",
    "store_calendar_event",
    "search_calendar_events",
    "delete_month_calendar_events",
    "delete_calendar_event",
    "_ensure_calendar_collection",
    "_calendar_collection_name",
    "_cal_qdrant_client",
    "_CALENDAR_EMBEDDING_DIM",
]
