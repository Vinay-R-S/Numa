import importlib
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


log = logging.getLogger(__name__)

_CALENDAR_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2



class SemanticMemoryService:
    """
    Semantic memory backed by Qdrant and pluggable embeddings.

    Defaults are tuned for fast local retrieval with compact vectors:
    - Provider: local (sentence-transformers)
    - Local model: sentence-transformers/all-MiniLM-L6-v2
    - Dimensions: 384
    - Distance: cosine
    """

    def __init__(self) -> None:
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.local_embedding_model = (
            os.getenv("HUGGINGFACE_EMBEDDING_MODEL")
            or "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "numa_agent_memory")
        self.context_limit = int(os.getenv("MEMORY_CONTEXT_LIMIT", "4"))
        self.recreate_collection_on_dim_mismatch = (
            os.getenv("MEMORY_RECREATE_COLLECTION_ON_DIM_MISMATCH", "false").strip().lower()
            in {"1", "true", "yes", "y", "on"}
        )

        self.openai_api_key = self._normalize_openai_key(os.getenv("OPENAI_API_KEY", ""))
        self.qdrant_url = self._normalize_qdrant_url(
            os.getenv("QDRANT_URL_ENDPOINT")
            or os.getenv("QDRANT_URL")
            or os.getenv("QDRANT_CLOUD_URL", "")
        )
        self.qdrant_api_key = self._normalize_secret(
            os.getenv("QDRANT_API_KEY") or os.getenv("QDRANT_CLOUD_API_KEY", "")
        )

        self.embedding_retry_after = timedelta(
            seconds=max(30, int(os.getenv("EMBEDDING_RETRY_AFTER_SECONDS", "300")))
        )
        self._embeddings_disabled_until: Optional[datetime] = None
        self._last_embedding_error: str = ""
        self._last_embedding_error_at: Optional[datetime] = None

    @staticmethod
    def _normalize_openai_key(value: str) -> str:
        key = (value or "").strip().strip('"').strip("'")
        lowered = key.lower()
        if lowered in {"", "your_openai_key", "your_openai_api_key", "openai_api_key"}:
            return ""
        return key

    @staticmethod
    def _normalize_secret(value: str) -> Optional[str]:
        secret = (value or "").strip().strip('"').strip("'")
        lowered = secret.lower()
        if lowered in {"", "your_qdrant_api_key", "qdrant_api_key"}:
            return None
        return secret

    @staticmethod
    def _normalize_qdrant_url(value: str) -> str:
        url = (value or "").strip().strip('"').strip("'").rstrip("/")
        lowered = url.lower()
        if lowered in {"", "your_qdrant_url", "qdrant_url", "qdrant_url_endpoint"}:
            return ""
        if "://" not in url:
            url = f"https://{url}"
        return url

    @staticmethod
    def _embedding_cache_dir() -> str:
        server_root = Path(__file__).resolve().parents[2]
        raw = (
            os.getenv("HUGGINGFACE_MODEL_CACHE_DIR")
            or ""
        ).strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                base = server_root.parent if path.parts and path.parts[0].lower() == "server" else server_root
                path = base / path
            return str(path)
        return str(server_root / "models")

    @property
    def enabled(self) -> bool:
        if not self.qdrant_url:
            return False

        if self.embedding_provider == "openai":
            return bool(self.openai_api_key)

        if self.embedding_provider == "local":
            return True

        return False

    @property
    def qdrant_mode(self) -> str:
        if not self.qdrant_url:
            return "disabled"
        return "cloud" if self.qdrant_api_key else "remote"

    @property
    def qdrant_host(self) -> str:
        if not self.qdrant_url:
            return ""
        parsed = urlparse(self.qdrant_url)
        return parsed.netloc or self.qdrant_url

    @staticmethod
    def _safe_collection_part(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", (value or "").strip())
        cleaned = cleaned.strip("_-").lower()
        return cleaned or "unknown_user"

    def user_collection_name(self, user_id: str, domain: str) -> str:
        user_part = self._safe_collection_part(user_id)
        domain_part = self._safe_collection_part(domain)
        name = f"{user_part}_{domain_part}"
        if len(name) <= 255:
            return name

        digest = uuid.uuid5(uuid.NAMESPACE_URL, name).hex[:12]
        max_user_len = 255 - len(domain_part) - len(digest) - 2
        return f"{user_part[:max_user_len]}_{domain_part}_{digest}"

    def memory_collection_name(self, user_id: str) -> str:
        return self.user_collection_name(user_id, "memory")

    @lru_cache(maxsize=1)
    def _deps(self) -> Optional[dict]:
        if not self.enabled:
            return None

        try:
            qdrant_client_module = importlib.import_module("qdrant_client")
            qdrant_models_module = importlib.import_module("qdrant_client.models")

            deps = {
                "QdrantClient": getattr(qdrant_client_module, "QdrantClient"),
                "Distance": getattr(qdrant_models_module, "Distance"),
                "VectorParams": getattr(qdrant_models_module, "VectorParams"),
                "PointStruct": getattr(qdrant_models_module, "PointStruct"),
                "PointIdsList": getattr(qdrant_models_module, "PointIdsList"),
                "Filter": getattr(qdrant_models_module, "Filter"),
                "FieldCondition": getattr(qdrant_models_module, "FieldCondition"),
                "MatchValue": getattr(qdrant_models_module, "MatchValue"),
            }

            if self.embedding_provider == "openai":
                openai_module = importlib.import_module("openai")
                deps["OpenAI"] = getattr(openai_module, "OpenAI")
            elif self.embedding_provider == "local":
                sentence_module = importlib.import_module("sentence_transformers")
                deps["SentenceTransformer"] = getattr(sentence_module, "SentenceTransformer")
            else:
                log.warning("Unsupported embedding provider '%s'.", self.embedding_provider)
                return None

            return deps
        except Exception as exc:
            log.warning("Semantic memory dependencies unavailable: %s", exc)
            return None

    @lru_cache(maxsize=1)
    def _openai_client(self) -> Any:
        if self.embedding_provider != "openai":
            return None

        deps = self._deps()
        if not deps or "OpenAI" not in deps:
            return None
        return deps["OpenAI"](api_key=self.openai_api_key)

    @lru_cache(maxsize=1)
    def _local_embedder(self) -> Any:
        if self.embedding_provider != "local":
            return None

        deps = self._deps()
        if not deps or "SentenceTransformer" not in deps:
            return None

        try:
            cache_dir = self._embedding_cache_dir()
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            return deps["SentenceTransformer"](
                self.local_embedding_model,
                cache_folder=cache_dir,
            )
        except Exception as exc:
            log.warning("Failed to load local embedding model '%s': %s", self.local_embedding_model, exc)
            return None

    @lru_cache(maxsize=1)
    def _qdrant_client(self) -> Any:
        deps = self._deps()
        if not deps:
            return None

        return deps["QdrantClient"](url=self.qdrant_url, api_key=self.qdrant_api_key)

    def _ensure_collection(
        self,
        collection_name: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> bool:
        target_collection = collection_name or self.collection_name
        target_dimensions = dimensions or self.embedding_dimensions
        deps = self._deps()
        qdrant = self._qdrant_client()
        if not deps or not qdrant:
            return False

        try:
            exists = qdrant.collection_exists(target_collection)
            if exists:
                try:
                    collection_info = qdrant.get_collection(target_collection)
                    existing_size = self._collection_vector_size(collection_info)
                    if existing_size and existing_size != target_dimensions:
                        if self.recreate_collection_on_dim_mismatch:
                            log.warning(
                                "Recreating Qdrant collection '%s' due to dimension mismatch (%s -> %s).",
                                target_collection,
                                existing_size,
                                target_dimensions,
                            )
                            qdrant.delete_collection(target_collection)
                            exists = False
                        else:
                            log.warning(
                                "Qdrant collection '%s' has dimension %s but expected %s.",
                                target_collection,
                                existing_size,
                                target_dimensions,
                            )
                            return False
                except Exception as exc:
                    log.warning("Failed to inspect Qdrant collection config: %s", exc)

            if exists:
                return True

            qdrant.create_collection(
                collection_name=target_collection,
                vectors_config=deps["VectorParams"](
                    size=target_dimensions,
                    distance=deps["Distance"].COSINE,
                ),
            )
            return True
        except Exception as exc:
            log.warning("Failed to ensure Qdrant collection '%s': %s", target_collection, exc)
            return False

    @staticmethod
    def _collection_vector_size(collection_info: Any) -> Optional[int]:
        try:
            config = getattr(collection_info, "config", None)
            params = getattr(config, "params", None)
            vectors = getattr(params, "vectors", None)

            if isinstance(vectors, dict):
                first = next(iter(vectors.values()), None)
                size = getattr(first, "size", None)
                return int(size) if size is not None else None

            size = getattr(vectors, "size", None)
            return int(size) if size is not None else None
        except Exception:
            return None

    def _coerce_dimensions(self, vector: List[float]) -> List[float]:
        size = len(vector)
        if size == self.embedding_dimensions:
            return vector
        if size > self.embedding_dimensions:
            return vector[: self.embedding_dimensions]
        return vector + [0.0] * (self.embedding_dimensions - size)

    def _embed_local(self, text: str) -> Optional[List[float]]:
        try:
            try:
                from src.embedder import embedder  # type: ignore
            except ImportError:
                from ..embedder import embedder  # type: ignore

            vector = embedder.embed(text)
            if vector:
                return self._coerce_dimensions(vector)
        except Exception as exc:
            log.warning("Shared local embedder unavailable: %s", exc)

        embedder = self._local_embedder()
        if not embedder:
            return None

        try:
            vector = embedder.encode(text, normalize_embeddings=True)
            if hasattr(vector, "tolist"):
                vector = vector.tolist()

            if isinstance(vector, list) and vector and isinstance(vector[0], list):
                vector = vector[0]

            if not isinstance(vector, list):
                return None

            return self._coerce_dimensions([float(v) for v in vector])
        except Exception as exc:
            log.warning("Local embedding generation failed: %s", exc)
            return None

    def _embed(self, text: str) -> Optional[List[float]]:
        if self.embedding_provider == "local":
            return self._embed_local(text)

        client = self._openai_client()
        if not client:
            return None

        now = datetime.now(timezone.utc)
        if self._embeddings_disabled_until and now < self._embeddings_disabled_until:
            return None

        if self._embeddings_disabled_until and now >= self._embeddings_disabled_until:
            self._embeddings_disabled_until = None

        try:
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=self.embedding_dimensions,
            )
            return self._coerce_dimensions(response.data[0].embedding)
        except TypeError:
            # Some SDK versions may not support dimensions for this call signature.
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return self._coerce_dimensions(response.data[0].embedding)
        except Exception as exc:
            msg = str(exc)
            lowered = msg.lower()
            now = datetime.now(timezone.utc)

            if "insufficient_quota" in lowered:
                self._embeddings_disabled_until = now + self.embedding_retry_after
                self._last_embedding_error = "insufficient_quota"
                self._last_embedding_error_at = now
                log.warning(
                    "Embedding disabled for %ss due to OpenAI insufficient quota.",
                    int(self.embedding_retry_after.total_seconds()),
                )
                return None

            if "rate_limit" in lowered or "429" in lowered:
                self._embeddings_disabled_until = now + timedelta(seconds=60)
                self._last_embedding_error = "rate_limited"
                self._last_embedding_error_at = now
                log.warning("Embedding temporarily paused for 60s due to rate limiting.")
                return None

            log.warning("Embedding generation failed: %s", exc)
            return None

    @staticmethod
    def _stable_point_id(namespace: str, user_id: str, external_id: str) -> str:
        return uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"numa:{namespace}:{user_id}:{external_id}",
        ).hex

    @staticmethod
    def _qdrant_point_id(point_id: str) -> str:
        return str(uuid.UUID(point_id))

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


# ══════════════════════════════════════════════════════════════════════════════
# CALENDAR RAG - per-user Qdrant collections ("{user_id}_calendar")
# ══════════════════════════════════════════════════════════════════════════════
# Uses the shared CachedEmbedder singleton so the model is only loaded once.

def _cal_qdrant_client():
    """Return the same Qdrant Cloud client used by the memory service."""
    return memory_service._qdrant_client()


def _calendar_collection_name(user_id: str) -> str:
    return memory_service.user_collection_name(user_id, "calendar")


def _ensure_calendar_collection(user_id: str) -> bool:
    """
    Create the user's calendar Qdrant collection if it doesn't exist.
    Idempotent - safe to call on every ingest.
    """
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
            for field in ("user_id", "app", "month"):
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
            for field in ("user_id", "app", "month"):
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
