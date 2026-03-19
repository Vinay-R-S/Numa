import importlib
import logging
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, List, Optional


log = logging.getLogger(__name__)


class SemanticMemoryService:
    """
    Semantic memory backed by Qdrant and OpenAI embeddings.

    Defaults are tuned for high retrieval quality while keeping vectors medium-sized:
    - Model: text-embedding-3-large
    - Dimensions: 1536
    - Distance: cosine
    """

    def __init__(self) -> None:
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "numa_agent_memory")
        self.context_limit = int(os.getenv("MEMORY_CONTEXT_LIMIT", "4"))

        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.qdrant_url = os.getenv("QDRANT_URL", "").strip()
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None

    @property
    def enabled(self) -> bool:
        return bool(self.openai_api_key and self.qdrant_url)

    @lru_cache(maxsize=1)
    def _deps(self) -> Optional[dict]:
        if not self.enabled:
            return None

        try:
            openai_module = importlib.import_module("openai")
            qdrant_client_module = importlib.import_module("qdrant_client")
            qdrant_models_module = importlib.import_module("qdrant_client.models")

            return {
                "OpenAI": getattr(openai_module, "OpenAI"),
                "QdrantClient": getattr(qdrant_client_module, "QdrantClient"),
                "Distance": getattr(qdrant_models_module, "Distance"),
                "VectorParams": getattr(qdrant_models_module, "VectorParams"),
                "PointStruct": getattr(qdrant_models_module, "PointStruct"),
                "PointIdsList": getattr(qdrant_models_module, "PointIdsList"),
                "Filter": getattr(qdrant_models_module, "Filter"),
                "FieldCondition": getattr(qdrant_models_module, "FieldCondition"),
                "MatchValue": getattr(qdrant_models_module, "MatchValue"),
            }
        except Exception as exc:
            log.warning("Semantic memory dependencies unavailable: %s", exc)
            return None

    @lru_cache(maxsize=1)
    def _openai_client(self) -> Any:
        deps = self._deps()
        if not deps:
            return None
        return deps["OpenAI"](api_key=self.openai_api_key)

    @lru_cache(maxsize=1)
    def _qdrant_client(self) -> Any:
        deps = self._deps()
        if not deps:
            return None
        return deps["QdrantClient"](url=self.qdrant_url, api_key=self.qdrant_api_key)

    def _ensure_collection(self) -> bool:
        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return False

        try:
            exists = qdrant.collection_exists(self.collection_name)
            if exists:
                return True

            qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=deps["VectorParams"](
                    size=self.embedding_dimensions,
                    distance=deps["Distance"].COSINE,
                ),
            )
            return True
        except Exception as exc:
            log.warning("Failed to ensure Qdrant collection '%s': %s", self.collection_name, exc)
            return False

    def _embed(self, text: str) -> Optional[List[float]]:
        client = self._openai_client()
        if not client:
            return None

        try:
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=self.embedding_dimensions,
            )
            return response.data[0].embedding
        except TypeError:
            # Some SDK versions may not support dimensions for this call signature.
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            log.warning("Embedding generation failed: %s", exc)
            return None

    @staticmethod
    def _stable_point_id(namespace: str, user_id: str, external_id: str) -> str:
        return uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"numa:{namespace}:{user_id}:{external_id}",
        ).hex

    def _upsert_text_point(self, point_id: str, text: str, payload: dict) -> None:
        if not self.enabled:
            return

        vector = self._embed(text)
        if not vector:
            return
        if not self._ensure_collection():
            return

        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return

        try:
            point = deps["PointStruct"](id=point_id, vector=vector, payload=payload)
            qdrant.upsert(collection_name=self.collection_name, points=[point], wait=False)
        except Exception as exc:
            log.warning("Failed to upsert semantic memory point: %s", exc)

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

        self._upsert_text_point(uuid.uuid4().hex, content, payload)

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
        self._upsert_text_point(point_id, text, payload)

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
        self._upsert_text_point(point_id, text, payload)

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
        try:
            qdrant.delete(
                collection_name=self.collection_name,
                points_selector=deps["PointIdsList"](points=[point_id]),
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
        if not self._ensure_collection():
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
                collection_name=self.collection_name,
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
