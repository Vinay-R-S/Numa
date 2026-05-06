"""Pydantic schemas for the LeetCode sub-agent API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Stats ─────────────────────────────────────────────────────────────────────

class LeetCodeStatsRequest(BaseModel):
    username: str


class LeetCodeStats(BaseModel):
    username: str
    total_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    acceptance_rate: float = 0.0
    ranking: int = 0
    contribution_points: int = 0
    reputation: int = 0
    recent_submissions: List[Dict[str, Any]] = []


# ── Chat ──────────────────────────────────────────────────────────────────────

class LeetCodeChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class LeetCodeChatRequest(BaseModel):
    query: str
    history: List[LeetCodeChatMessage] = []
    model: Optional[str] = None


class LeetCodeChatResponse(BaseModel):
    response: str
    success: bool = True
    delegated_to: Optional[str] = None
