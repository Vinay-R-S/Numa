"""LeetCode feature service (NUMA-117 P4, PLAN 2.1 / 5.2 / 21.1).

`LeetCodeService` owns what the routes held inline: the public profile stats
fetch with its 404/502 error mapping, and the sub-agent chat delegation. The
GraphQL client is injected through the constructor instead of being a module
global created at import time.

The LangGraph sub-agent moved to `agent.py`; its public entrypoint is re-exported
here so `master_agent.orchestrator` keeps its existing import path.

Errors: methods raise `core.errors.AppError` with the status code the route used
to raise directly; `router._http_error` maps them back to HTTP.
"""
from __future__ import annotations

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


class LeetCodeService(BaseService):
    """LeetCode profile stats and chat behind the /api/leetcode routes."""

    def __init__(
        self,
        client: Optional[LeetCodeClient] = None,
        chat_agent: Optional[Callable[..., Dict]] = None,
    ) -> None:
        super().__init__()
        self.client = client or LeetCodeClient()
        self.chat_agent = chat_agent or run_leetcode_agent_chat

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self, username: str) -> Dict:
        """Public profile stats. An unknown user is a 404, an upstream fault a 502."""
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
            return LeetCodeStats(**stats).model_dump()
        except ValidationError as exc:
            raise self._upstream_error(exc) from exc

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
