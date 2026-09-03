"""
LeetCode Router
=================
Endpoints
---------
GET  /api/leetcode/stats?username=...  - LeetCode profile stats (JWT-protected)
POST /api/leetcode/chat                - LeetCode sub-agent chat (JWT-protected)

Thin routing layer (NUMA-117 P4, PLAN 2.1 / 18): the GraphQL client lives in
leetcode_client.py, the LangGraph agent in agent.py, and the orchestration behind
these routes in the `Depends`-injected `LeetCodeService`.

Both routes require a JWT since NUMA-133. The profile data is public, so nothing
leaked, but the stats route made two calls to leetcode.com per request and anyone
who knew the URL could drive it - an unauthenticated way to spend this server's
outbound quota. The service caches per username; the route bounds what a username
may look like, so junk is rejected here rather than forwarded upstream.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from ..core.errors import AppError
from .schemas import (
    LeetCodeChatRequest,
    LeetCodeChatResponse,
    LeetCodeStats,
)
from .service import LeetCodeService, leetcode_service, run_leetcode_agent_chat  # noqa: F401  re-exported

log = logging.getLogger(__name__)

# Mounted at both /leetcode and /api/leetcode (main.py alias).
router = APIRouter(prefix="/leetcode", tags=["leetcode"])


def get_leetcode_service() -> LeetCodeService:
    return leetcode_service


def _http_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


# ── Stats (JWT-protected) ────────────────────────────────────────────────────

#: LeetCode handles are letters, digits, underscore, hyphen and dot. Bounding the
#: shape here keeps a 10KB query string from becoming a GraphQL call (PLAN 22.1).
USERNAME_PATTERN = r"^[A-Za-z0-9._-]+$"
USERNAME_MAX_LENGTH = 39


@router.get("/stats", response_model=LeetCodeStats, summary="Fetch LeetCode profile stats")
def get_leetcode_stats(
    username: str = Query(
        ...,
        min_length=1,
        max_length=USERNAME_MAX_LENGTH,
        pattern=USERNAME_PATTERN,
        description="LeetCode username",
    ),
    current_user: dict = Depends(get_current_user),
    service: LeetCodeService = Depends(get_leetcode_service),
):
    try:
        stats = service.get_stats(username)
    except AppError as exc:
        raise _http_error(exc) from exc

    return LeetCodeStats(**stats)


# ── Chat (JWT-protected) ─────────────────────────────────────────────────────

@router.post("/chat", response_model=LeetCodeChatResponse, summary="Chat with the LeetCode sub-agent")
def leetcode_chat(
    request: LeetCodeChatRequest,
    current_user: dict = Depends(get_current_user),
    service: LeetCodeService = Depends(get_leetcode_service),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result = service.chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=user_id,
        model=request.model,
    )
    return LeetCodeChatResponse(**result)
