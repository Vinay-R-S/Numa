"""Qdrant client, configuration, embedding bridge, and collection management.

NUMA-107 P3 (PLAN 16.5): the infrastructure half of the former memory god-class.
``MemoryClient`` owns env config, dependency loading, the Qdrant client, embedding
generation, collection ensure/index helpers, and point/collection id helpers.
``SemanticMemoryService`` (service.py) subclasses this and adds the store/search
operations, so ``memory_service`` continues to expose every attribute callers use.
"""
import importlib
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse


log = logging.getLogger(__name__)


class MemoryClient:
    """
    Infrastructure for semantic memory backed by Qdrant and pluggable embeddings.

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
                self._ensure_payload_indexes(qdrant, target_collection, ("user_id", "source"))
                return True

            qdrant.create_collection(
                collection_name=target_collection,
                vectors_config=deps["VectorParams"](
                    size=target_dimensions,
                    distance=deps["Distance"].COSINE,
                ),
            )
            self._ensure_payload_indexes(qdrant, target_collection, ("user_id", "source"))
            return True
        except Exception as exc:
            log.warning("Failed to ensure Qdrant collection '%s': %s", target_collection, exc)
            return False

    @staticmethod
    def _ensure_payload_indexes(qdrant: Any, collection_name: str, fields: tuple[str, ...]) -> None:
        for field in fields:
            try:
                qdrant.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema="keyword",
                )
            except Exception:
                pass

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
