"""Pydantic schemas for the Health sub-agent API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Chat ──────────────────────────────────────────────────────────────────────

class HealthChatMessage(BaseModel):
    role: str
    content: str


class HealthChatRequest(BaseModel):
    query: str
    history: List[HealthChatMessage] = []
    model: Optional[str] = None


class HealthChatResponse(BaseModel):
    response: str
    success: bool = True
    delegated_to: Optional[str] = None
    refresh_health: bool = False


# ── Snapshot data ─────────────────────────────────────────────────────────────

class HealthSnapshotOut(BaseModel):
    id: str
    user_id: str
    source: str
    snapshot_date: date
    steps: Optional[int] = None
    active_minutes: Optional[int] = None
    calories: Optional[int] = None
    distance_km: Optional[float] = None
    sleep_hours: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    heart_points: Optional[float] = None
    sleep_stages: Optional[Dict[str, Any]] = None
    activities: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Status ────────────────────────────────────────────────────────────────────

class HealthStatusOut(BaseModel):
    google_fit_configured: bool = False
    strava_configured: bool = False
    snapshots_today: int = 0
    total_snapshots: int = 0


# ── Sync ──────────────────────────────────────────────────────────────────────

class HealthSyncOut(BaseModel):
    ok: bool
    source: str
    snapshot_date: Optional[str] = None
    detail: Optional[str] = None
