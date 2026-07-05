"""
Health Sub-Agent FastAPI Router
================================
Endpoints
---------
GET  /health-agent/status         - Check Google Fit + Strava config
GET  /health-agent/snapshots      - Fetch stored snapshots (7+1 day window)
POST /health-agent/sync/google-fit - Sync today's Google Fit data to Supabase
POST /health-agent/sync/strava    - Sync today's Strava data to Supabase
POST /health-agent/chat           - Invoke Health sub-agent (LangGraph)
POST /health-agent/purge          - Manual purge of old snapshots (internal)

Storage
-------
health_snapshots table: one row per (user, source, date). Rolling 7+1 day window.
Purged automatically at 8 AM daily via APScheduler.

Thin routing layer (NUMA-108 P3, PLAN 16.6): helpers live in utils.py, DB/vector
persistence in persistence.py, provider sync in sync.py, the agent in service.py.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from .persistence import (
    get_health_intraday_snapshot,
    get_health_snapshots,
    purge_old_health_snapshots,
)
from .schemas import (
    HealthChatRequest,
    HealthChatResponse,
    HealthIntradayOut,
    HealthIntradayBucketOut,
    HealthSnapshotOut,
    HealthStatusOut,
    HealthSyncOut,
)
from .sync import (
    _get_user_timezone,
    _is_google_fit_configured,
    _is_strava_configured,
    sync_google_fit_for_user,
    sync_health_for_user,
    sync_strava_for_user,
)
from .utils import _bucket_for_api, _empty_intraday_buckets, _intraday_bounds

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health-agent", tags=["health-agent"])


@router.get("/status", response_model=HealthStatusOut)
def health_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    snapshots = get_health_snapshots(user_id or "", days=8) if user_id else []
    today_count = sum(1 for s in snapshots if s.get("snapshot_date") == date.today())
    return HealthStatusOut(
        google_fit_configured=_is_google_fit_configured(),
        strava_configured=_is_strava_configured(),
        snapshots_today=today_count,
        total_snapshots=len(snapshots),
    )


@router.get("/snapshots", response_model=List[HealthSnapshotOut])
def get_snapshots(
    source: Optional[str] = Query(None, description="google_fit or strava"),
    days: int = Query(8, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    rows = get_health_snapshots(user_id, source=source, days=days)
    return [
        HealthSnapshotOut(
            id=str(r["id"]),
            user_id=str(r["user_id"]),
            source=r["source"],
            snapshot_date=r["snapshot_date"],
            steps=r.get("steps"),
            active_minutes=r.get("active_minutes"),
            calories=r.get("calories"),
            distance_km=r.get("distance_km"),
            sleep_hours=r.get("sleep_hours"),
            heart_rate_bpm=r.get("heart_rate_bpm"),
            heart_points=r.get("heart_points"),
            sleep_start_at=r.get("sleep_start_at"),
            sleep_end_at=r.get("sleep_end_at"),
            sleep_stages=r.get("sleep_stages"),
            sleep_segments=r.get("sleep_segments"),
            activities=r.get("activities"),
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
        )
        for r in rows
    ]


@router.get("/intraday", response_model=HealthIntradayOut)
def get_intraday(
    snapshot_date: date = Query(..., description="Date to load in YYYY-MM-DD format"),
    source: str = Query("google_fit", description="google_fit"),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    if source != "google_fit":
        raise HTTPException(status_code=400, detail="Intraday health data is currently available for Google Fit only")

    tz = _get_user_timezone(user_id)
    row = get_health_intraday_snapshot(user_id, snapshot_date=snapshot_date, source=source)
    if not row:
        window_start_at, window_end_at = _intraday_bounds(snapshot_date, tz)
        buckets = _empty_intraday_buckets(window_start_at, window_end_at)
        return HealthIntradayOut(
            id=None,
            user_id=user_id,
            source=source,
            snapshot_date=snapshot_date,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            bucket_minutes=60,
            steps=0,
            calories=0,
            distance_km=0,
            buckets=[HealthIntradayBucketOut(**_bucket_for_api(bucket, tz)) for bucket in buckets],
        )

    buckets = row.get("buckets") or []
    return HealthIntradayOut(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        source=row["source"],
        snapshot_date=row["snapshot_date"],
        window_start_at=row["window_start_at"],
        window_end_at=row["window_end_at"],
        bucket_minutes=row["bucket_minutes"],
        steps=row.get("steps") or 0,
        calories=row.get("calories") or 0,
        distance_km=row.get("distance_km") or 0,
        buckets=[HealthIntradayBucketOut(**_bucket_for_api(bucket, tz)) for bucket in buckets],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("/sync/google-fit", response_model=HealthSyncOut)
def sync_google_fit(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    result = sync_google_fit_for_user(user_id)
    return HealthSyncOut(**result)


@router.post("/sync/strava", response_model=HealthSyncOut)
def sync_strava(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    result = sync_strava_for_user(user_id)
    return HealthSyncOut(**result)


@router.post("/sync/all")
def sync_all(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    return sync_health_for_user(user_id)


@router.post("/chat", response_model=HealthChatResponse)
def health_chat(
    request: HealthChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    from .service import run_health_agent_chat
    result = run_health_agent_chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=user_id,
        model=request.model,
    )
    return HealthChatResponse(**result)


@router.post("/internal/purge", include_in_schema=False)
def purge_old_snapshots():
    """Called by the APScheduler daily 8 AM job."""
    deleted = purge_old_health_snapshots()
    return {"ok": True, "deleted": deleted}
