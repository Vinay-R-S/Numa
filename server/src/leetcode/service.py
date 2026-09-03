"""LeetCode feature service (NUMA-117 P4, NUMA-133 P6, PLAN 2.1 / 5.2 / 21.1 / 9).

`LeetCodeService` owns what the routes held inline: the public profile stats
fetch with its 404/502 error mapping, and the sub-agent chat delegation. The
GraphQL client is injected through the constructor instead of being a module
global created at import time.

The LangGraph sub-agent moved to `agent.py`; its public entrypoint is re-exported
here so `master_agent.orchestrator` keeps its existing import path.

Errors: methods raise `core.errors.AppError` with the status code the route used
to raise directly; `router._http_error` maps them back to HTTP.

Stats are cached per username since NUMA-133. One `/leetcode/stats` call makes two
requests to leetcode.com (profile + recent submissions), and the route was open to
anyone, so the endpoint was an unauthenticated way to make this server hammer
leetcode.com. The route takes a JWT now; the cache is the other half, so a signed-in
caller in a loop cannot do the same thing more slowly.
"""
from __future__ import annotations

import copy
import threading
import time
from typing import Callable, Dict, List, Optional

from pydantic import ValidationError

from ..core.base import BaseService
from ..core.errors import AppError
from .agent import (  # noqa: F401  re-exported for existing import paths
    LEETCODE_AGENT_SYSTEM_PROMPT,
    LeetCodeAgentState,
    run_leetcode_agent_chat,
)
from .leetcode_client import LeetCodeClient
from .schemas import LeetCodeStats

#: How long a username's stats stay fresh. Solve counts move slowly; five minutes
#: keeps the panel current while collapsing a burst of reloads into one fetch.
STATS_CACHE_TTL_SECONDS = 300

#: Cap on distinct usernames held, so a caller cycling names cannot grow the
#: process without bound. Oldest entry goes first.
STATS_CACHE_MAX_ENTRIES = 256


class LeetCodeService(BaseService):
    """LeetCode profile stats and chat behind the /api/leetcode routes."""

    def __init__(
        self,
        client: Optional[LeetCodeClient] = None,
        chat_agent: Optional[Callable[..., Dict]] = None,
        cache_ttl_seconds: float = STATS_CACHE_TTL_SECONDS,
    ) -> None:
        super().__init__()
        self.client = client or LeetCodeClient()
        self.chat_agent = chat_agent or run_leetcode_agent_chat
        self.cache_ttl_seconds = cache_ttl_seconds
        # username -> (stored_at, stats). Sync routes run in a threadpool, so the
        # dict is guarded rather than assumed safe.
        self._stats_cache: Dict[str, tuple[float, Dict]] = {}
        self._cache_lock = threading.Lock()

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self, username: str) -> Dict:
        """Profile stats, cached per username.

        An unknown user is a 404 and an upstream fault a 502, unchanged. Only a
        successful fetch is cached: an error is never stored and never served, so
        a 404 for a name that gets created later is not sticky.
        """
        key = self._cache_key(username)
        cached = self._read_cache(key)
        if cached is not None:
            return cached

        try:
            stats = self.client.get_full_stats(username)
        except ValidationError as exc:
            raise self._upstream_error(exc) from exc
        except ValueError as exc:
            raise AppError(str(exc), status_code=404) from exc
        except Exception as exc:
            raise self._upstream_error(exc) from exc

        # Shaped here, not in the route: the old route built the response model
        # inside the same try, where `except ValueError` swallowed the Pydantic
        # ValidationError (it subclasses ValueError) and answered 404 "N
        # validation errors for LeetCodeStats". A malformed upstream payload is
        # an upstream fault, so it is now the 502 the route already documented.
        try:
            shaped = LeetCodeStats(**stats).model_dump()
        except ValidationError as exc:
            raise self._upstream_error(exc) from exc

        self._write_cache(key, shaped)
        return shaped

    # ── Stats cache ──────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(username: str) -> str:
        """The name as given, trimmed only.

        Deliberately not lowercased: LeetCode's `matchedUser` lookup may well be
        case-sensitive, and folding case would let a request for a name that does
        not exist be answered from a differently-cased one that does - turning a
        404 into someone else's stats. A differently-cased name simply fetches
        again, which costs one call and cannot be wrong.
        """
        return username.strip()

    def _read_cache(self, key: str) -> Optional[Dict]:
        with self._cache_lock:
            entry = self._stats_cache.get(key)
            if entry is None:
                return None

            stored_at, stats = entry
            if time.monotonic() - stored_at > self.cache_ttl_seconds:
                del self._stats_cache[key]
                return None

        # Deep, not shallow: `recent_submissions` is a list of dicts, so a
        # shallow copy would still hand out the cached inner objects.
        return copy.deepcopy(stats)

    def _write_cache(self, key: str, stats: Dict) -> None:
        with self._cache_lock:
            if key not in self._stats_cache and len(self._stats_cache) >= STATS_CACHE_MAX_ENTRIES:
                oldest = min(self._stats_cache, key=lambda k: self._stats_cache[k][0])
                del self._stats_cache[oldest]
            self._stats_cache[key] = (time.monotonic(), copy.deepcopy(stats))

    def _upstream_error(self, exc: Exception) -> AppError:
        self.log.error("LeetCode stats fetch failed: %s", exc)
        return AppError("Failed to fetch LeetCode stats", status_code=502)

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat(
        self,
        query: str,
        history: List[dict],
        user_id: Optional[str],
        model: Optional[str] = None,
    ) -> Dict:
        return self.chat_agent(query=query, history=history, user_id=user_id, model=model)


leetcode_service = LeetCodeService()
