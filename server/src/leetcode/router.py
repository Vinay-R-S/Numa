"""
LeetCode Sub-Agent FastAPI Router
===================================
Endpoints
---------
GET  /api/leetcode/stats?username=...  - public LeetCode profile stats
POST /api/leetcode/chat                - LeetCode sub-agent chat (JWT-protected)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from .leetcode_client import LeetCodeClient
from .schemas import (
    LeetCodeChatRequest,
    LeetCodeChatResponse,
    LeetCodeStats,
)
from .service import run_leetcode_agent_chat

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leetcode", tags=["leetcode"])

_client = LeetCodeClient()


# ── Stats (public profiles - no auth required) ───────────────────────────────

@router.get("/stats", response_model=LeetCodeStats, summary="Fetch LeetCode profile stats")
def get_leetcode_stats(username: str = Query(..., min_length=1, description="LeetCode username")):
    try:
        stats = _client.get_full_stats(username)
        return LeetCodeStats(**stats)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.error("LeetCode stats fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to fetch LeetCode stats")


# ── Chat (JWT-protected) ─────────────────────────────────────────────────────

@router.post("/chat", response_model=LeetCodeChatResponse, summary="Chat with the LeetCode sub-agent")
def leetcode_chat(
    request: LeetCodeChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result = run_leetcode_agent_chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=user_id,
        model=request.model,
    )
    return LeetCodeChatResponse(**result)
