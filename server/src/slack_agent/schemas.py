"""Pydantic schemas for the Slack sub-agent API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Chat ──────────────────────────────────────────────────────────────────────

class SlackChatMessage(BaseModel):
    role: str             # "user" | "assistant"
    content: str


class SlackChatRequest(BaseModel):
    query: str
    history: List[SlackChatMessage] = []
    model: Optional[str] = None


class SlackChatResponse(BaseModel):
    response: str
    success: bool = True
    delegated_to: Optional[str] = None
    refresh_slack: bool = False
    debug_info: Optional[Dict[str, Any]] = None


# ── Messages ──────────────────────────────────────────────────────────────────

class SlackMessageOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    slack_user_id: str
    slack_channel_id: str
    channel_name: Optional[str] = None
    text: Optional[str] = None
    ts: str
    thread_ts: Optional[str] = None
    message_type: str = "message"
    created_at: Optional[datetime] = None


# ── Channels ──────────────────────────────────────────────────────────────────

class SlackChannelOut(BaseModel):
    id: str
    slack_id: str
    name: Optional[str] = None
    team_id: str
    is_private: bool = False
    created_at: Optional[datetime] = None


# ── Auth / Status ─────────────────────────────────────────────────────────────

class SlackStatusOut(BaseModel):
    connected: bool
    slack_user_id: Optional[str] = None
    slack_team_id: Optional[str] = None
    team_name: Optional[str] = None
    bot_configured: bool = False   # True when SLACK_BOT_TOKEN env var is set


# ── Events (incoming webhook from Slack) ──────────────────────────────────────

class SlackEventPayload(BaseModel):
    token: Optional[str] = None
    type: str
    challenge: Optional[str] = None            # for URL verification
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = None
    event_time: Optional[int] = None
