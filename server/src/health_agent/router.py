"""
Health Sub-Agent FastAPI Router
================================
Endpoints
---------
GET  /health-agent/status          - Check Google Fit + Strava config
GET  /health-agent/snapshots       - Fetch stored snapshots (7+1 day window)
GET  /health-agent/intraday        - Hourly buckets for one day
POST /health-agent/sync/google-fit - Sync today's Google Fit data to Supabase
POST /health-agent/sync/strava     - Sync today's Strava data to Supabase
POST /health-agent/sync/all        - Sync the recent window from both providers
POST /health-agent/chat            - Invoke Health sub-agent (LangGraph)
POST /health-agent/internal/purge  - Manual purge of old snapshots (admin-only)

Storage
-------
health_snapshots table: one row per (user, source, date). Rolling 7+1 day window.
Purged automatically at 8 AM daily via APScheduler.

Thin routing layer (NUMA-108 P3 / NUMA-116 P4, PLAN 2.1 / 16.6 / 18): helpers
live in utils.py, DB/vector persistence in persistence.py, provider sync in
sync.py, the LangGraph agent in agent.py, and the orchestration behind these
routes in the `Depends`-injected `HealthService`.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user, require_admin
from ..core.errors import AppError
from .schemas import (
    HealthChatRequest,
    HealthChatResponse,
    HealthIntradayOut,
    HealthSnapshotOut,
    HealthStatusOut,
    HealthSyncOut,
)
from .service import HealthService, health_service, run_health_agent_chat  # noqa: F401  re-exported

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health-agent", tags=["health-agent"])


def get_health_service() -> HealthService:
    return health_service


def _require_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    return str(user_id)


def _http_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/status", response_model=HealthStatusOut)
def health_status(
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    return HealthStatusOut(**service.get_status(current_user.get("sub")))


@router.get("/snapshots", response_model=List[HealthSnapshotOut])
def get_snapshots(
    source: Optional[str] = Query(None, description="google_fit or strava"),
    days: int = Query(8, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    rows = service.list_snapshots(_require_user_id(current_user), source=source, days=days)
    return [HealthSnapshotOut(**row) for row in rows]


@router.get("/intraday", response_model=HealthIntradayOut)
def get_intraday(
    snapshot_date: date = Query(..., description="Date to load in YYYY-MM-DD format"),
    source: str = Query("google_fit", description="google_fit"),
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    try:
        data = service.get_intraday(
            _require_user_id(current_user),
            snapshot_date=snapshot_date,
            source=source,
        )
    except AppError as exc:
        raise _http_error(exc) from exc

    return HealthIntradayOut(**data)


@router.post("/sync/google-fit", response_model=HealthSyncOut)
def sync_google_fit(
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    return HealthSyncOut(**service.sync_google_fit(_require_user_id(current_user)))


@router.post("/sync/strava", response_model=HealthSyncOut)
def sync_strava(
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    return HealthSyncOut(**service.sync_strava(_require_user_id(current_user)))


@router.post("/sync/all")
def sync_all(
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    return service.sync_all(_require_user_id(current_user))


@router.post("/chat", response_model=HealthChatResponse)
def health_chat(
    request: HealthChatRequest,
    current_user: dict = Depends(get_current_user),
    service: HealthService = Depends(get_health_service),
):
    result = service.chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=current_user.get("sub"),
        model=request.model,
    )
    return HealthChatResponse(**result)


@router.post("/internal/purge", include_in_schema=False)
def purge_old_snapshots(
    current_user: dict = Depends(require_admin),
    service: HealthService = Depends(get_health_service),
):
    """Operator-triggered purge, admin-only (NUMA-130 P6, PLAN 8).

    The daily 8 AM APScheduler job does not come through here: it calls
    `purge_old_health_snapshots()` in-process from `core/scheduler.py`. This route
    is the manual trigger, and it deletes every user's snapshots older than the
    window, so it takes the same gate as the other server-wide operations.
    """
    return service.purge_old_snapshots()
