"""
Shared, cached MiniLM embedding singleton for the NUMA server.

The model is downloaded once from Hugging Face and stored under HUGGINGFACE_MODEL_CACHE_DIR
(default: server/models/).  On subsequent starts it loads from disk - no
network required.

Usage anywhere in the server:
    from src.embedder import embedder
    vector = embedder.embed("some text")   # List[float], dim=384
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_HUGGINGFACE_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def embedding_model_name() -> str:
    return (
        os.getenv("HUGGINGFACE_EMBEDDING_MODEL")
        or DEFAULT_HUGGINGFACE_EMBEDDING_MODEL
    ).strip()


def _model_cache_dir() -> str:
    server_root = Path(__file__).resolve().parents[1]
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
    # Default: <server_root>/models/
    return str(server_root / "models")


# ── Singleton ──────────────────────────────────────────────────────────────────

class _CachedEmbedder:
    """
    Thread-safe, lazy-loading wrapper around sentence-transformers.

    The SentenceTransformer object is loaded on first call to embed() and
    kept alive for the lifetime of the process.  Subsequent calls are free.
    """

    def __init__(self) -> None:
        self._model = None
        self._failed = False

    # ------------------------------------------------------------------
    def _load(self):
        if self._model is not None or self._failed:
            return

        cache_dir = _model_cache_dir()
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            model_name = embedding_model_name()
            log.info(
                "Loading embedding model '%s' (cache: %s) …",
                model_name,
                cache_dir,
            )
            self._model = SentenceTransformer(
                model_name,
                cache_folder=cache_dir,
            )
            dim = self._model.get_sentence_embedding_dimension()
            log.info("Embedding model ready - dim=%d", dim)
        except Exception as exc:
            log.warning("Failed to load embedding model '%s': %s", embedding_model_name(), exc)
            self._failed = True

    # ------------------------------------------------------------------
    @property
    def dimension(self) -> int:
        self._load()
        if self._model is None:
            return 384  # MiniLM-L6 default
        return int(self._model.get_sentence_embedding_dimension())

    # ------------------------------------------------------------------
    def embed(self, text: str) -> Optional[List[float]]:
        """
        Embed *text* and return a normalised float list.
        Returns None if the model failed to load.
        """
        self._load()
        if self._model is None:
            return None
        try:
            vec = self._model.encode(text.strip(), normalize_embeddings=True)
            if hasattr(vec, "tolist"):
                vec = vec.tolist()
            if isinstance(vec, list) and vec and isinstance(vec[0], list):
                vec = vec[0]
            return [float(v) for v in vec]
        except Exception as exc:
            log.warning("embed() failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Embed multiple texts in one pass - more efficient than looping."""
        self._load()
        if self._model is None:
            return [None] * len(texts)
        try:
            vecs = self._model.encode(
                [t.strip() for t in texts],
                normalize_embeddings=True,
                batch_size=64,
            )
            return [[float(v) for v in row.tolist()] for row in vecs]
        except Exception as exc:
            log.warning("embed_batch() failed: %s", exc)
            return [None] * len(texts)


# ── Module-level singleton ─────────────────────────────────────────────────────

embedder = _CachedEmbedder()
