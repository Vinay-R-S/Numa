"""
Pydantic models shared across the NUMA backend.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    slack_user_id: str
    slack_team_id: str
    display_name: Optional[str] = None
    real_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Intent ────────────────────────────────────────────────────────────────────

class IntentResponse(BaseModel):
    intent: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    reflection: Optional[str] = None


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None
    source: str = "manual"
    slack_ts: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None


class TaskOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None
    source: str = "manual"
    slack_ts: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Plans ─────────────────────────────────────────────────────────────────────

class PlanBlock(BaseModel):
    label: str
    start_time: str
    end_time: str
    tag: Optional[str] = None


class PlanCreate(BaseModel):
    plan_date: date
    blocks: list[PlanBlock] = Field(default_factory=list)
    summary: Optional[str] = None


class PlanOut(BaseModel):
    id: str
    user_id: str
    plan_date: date
    blocks: list[Any] = Field(default_factory=list)
    summary: Optional[str] = None
    ai_model: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    slack_user_id: str
    slack_team_id: str
    channel_id: str
    channel_uuid: Optional[str] = None
    channel_name: Optional[str] = None
    text: Optional[str] = None
    ts: str
    thread_ts: Optional[str] = None
    message_type: str = "message"
    created_at: Optional[datetime] = None


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsOut(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    period_date: date
    tasks_completed: int = 0
    tasks_created: int = 0
    messages_sent: int = 0
    commands_used: int = 0
    productivity_score: Optional[int] = None
    created_at: Optional[datetime] = None


class AnalyticsPeriodOut(BaseModel):
    period: str
    data: list[AnalyticsOut]
    totals: dict[str, Any]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardToday(BaseModel):
    user: UserOut
    tasks_today: list[TaskOut] = Field(default_factory=list)
    tasks_completed_today: int = 0
    plan_today: Optional[PlanOut] = None
    unread_nudges: int = 0
    productivity_score: Optional[int] = None
    recent_messages: list[MessageOut] = Field(default_factory=list)


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str
    debug_info: Optional[dict[str, Any]] = None
