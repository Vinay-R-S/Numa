"""
Health Sub-Agent FastAPI Router
================================
Endpoints
---------
GET  /health-agent/status         - Check Google Fit + Strava config
GET  /health-agent/snapshots      - Fetch stored snapshots (7+1 day window)
POST /health-agent/sync/google-fit - Sync today's Google Fit data → Supabase
POST /health-agent/sync/strava    - Sync today's Strava data → Supabase
POST /health-agent/chat           - Invoke Health sub-agent (LangGraph)
POST /health-agent/purge          - Manual purge of old snapshots (internal)

Storage
-------
health_snapshots table: one row per (user, source, date). Rolling 7+1 day window.
Purged automatically at 8 AM daily via APScheduler.
"""
from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from ..memory import memory_service
from .schemas import (
    HealthChatRequest,
    HealthChatResponse,
    HealthSnapshotOut,
    HealthStatusOut,
    HealthSyncOut,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health-agent", tags=["health-agent"])


# ── Google Fit API (lazy singleton) ──────────────────────────────────────────

_google_fit_instance = None


def _get_google_fit():
    """Lazy-init Google Fit API client."""
    global _google_fit_instance
    if _google_fit_instance is None:
        from .google_fit_client import GoogleFitClient
        _google_fit_instance = GoogleFitClient()
    return _google_fit_instance


def _is_google_fit_configured() -> bool:
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    creds_file = os.getenv(
        'GOOGLE_FIT_CREDENTIALS_FILE',
        os.path.join(config_dir, 'credentials.json'),
    )
    return os.path.exists(creds_file)


def _is_strava_configured() -> bool:
    return bool(os.getenv("STRAVA_CLIENT_ID") and os.getenv("STRAVA_CLIENT_SECRET"))


# ── DB helpers ───────────────────────────────────────────────────────────────

def _row_to_dict(row, description) -> dict:
    return {col.name: val for col, val in zip(description, row)}


def _store_health_snapshot_vector(
    user_id: str,
    source: str,
    snapshot_date: date,
    data: Dict,
) -> None:
    try:
        activities = data.get("activities") or []
        if isinstance(activities, str):
            activities_text = activities[:300]
        elif isinstance(activities, list):
            activities_text = "; ".join(
                str(item.get("name") or item.get("type") or item)[:80]
                if isinstance(item, dict) else str(item)[:80]
                for item in activities[:6]
            )
        elif isinstance(activities, dict):
            activities_text = ", ".join(f"{k}: {v}" for k, v in list(activities.items())[:8])
        else:
            activities_text = ""

        sleep_stages = data.get("sleep_stages")
        if isinstance(sleep_stages, dict):
            sleep_text = ", ".join(f"{k}: {v}" for k, v in sleep_stages.items())
        else:
            sleep_text = str(sleep_stages or "")

        text = (
            f"Health snapshot for {snapshot_date.isoformat()} from {source}.\n"
            f"Steps: {data.get('steps') if data.get('steps') is not None else 'unknown'}.\n"
            f"Active minutes: {data.get('active_minutes') if data.get('active_minutes') is not None else 'unknown'}.\n"
            f"Calories: {data.get('calories') if data.get('calories') is not None else 'unknown'}.\n"
            f"Distance km: {data.get('distance_km') if data.get('distance_km') is not None else 'unknown'}.\n"
            f"Sleep hours: {data.get('sleep_hours') if data.get('sleep_hours') is not None else 'unknown'}.\n"
            f"Sleep stages: {sleep_text or 'none'}.\n"
            f"Activities: {activities_text or 'none'}."
        )
        memory_service.upsert_domain_text(
            user_id=user_id,
            domain="health",
            stable_key=f"{source}:{snapshot_date.isoformat()}",
            text=text,
            payload={
                "source": source,
                "snapshot_date": snapshot_date.isoformat(),
                "steps": data.get("steps"),
                "active_minutes": data.get("active_minutes"),
                "calories": data.get("calories"),
                "distance_km": data.get("distance_km"),
                "sleep_hours": data.get("sleep_hours"),
            },
        )
    except Exception as exc:
        log.warning("Health Qdrant upsert failed: %s", exc)


def upsert_health_snapshot(
    user_id: str,
    source: str,
    snapshot_date: date,
    data: Dict,
) -> bool:
    """Upsert one health snapshot row. Returns True on success."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.health_snapshots
                (user_id, source, snapshot_date, steps, active_minutes, calories,
                 distance_km, sleep_hours, sleep_stages, activities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, source, snapshot_date)
            DO UPDATE SET
                steps          = EXCLUDED.steps,
                active_minutes = EXCLUDED.active_minutes,
                calories       = EXCLUDED.calories,
                distance_km    = EXCLUDED.distance_km,
                sleep_hours    = EXCLUDED.sleep_hours,
                sleep_stages   = EXCLUDED.sleep_stages,
                activities     = EXCLUDED.activities,
                updated_at     = NOW()
            """,
            (
                user_id,
                source,
                snapshot_date,
                data.get("steps"),
                data.get("active_minutes"),
                data.get("calories"),
                data.get("distance_km"),
                data.get("sleep_hours"),
                json.dumps(data.get("sleep_stages")) if data.get("sleep_stages") else None,
                json.dumps(data.get("activities")) if data.get("activities") else None,
            ),
        )
        conn.commit()
        cur.close()
        _store_health_snapshot_vector(user_id, source, snapshot_date, data)
        return True
    except Exception as exc:
        log.warning("upsert_health_snapshot failed: %s", exc)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_health_snapshots(
    user_id: str,
    source: Optional[str] = None,
    days: int = 8,
) -> List[Dict]:
    """Fetch recent health snapshots for a user (up to N days)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cutoff = date.today() - timedelta(days=days)
        if source:
            cur.execute(
                """
                SELECT id, user_id, source, snapshot_date, steps, active_minutes,
                       calories, distance_km, sleep_hours, sleep_stages, activities,
                       created_at, updated_at
                FROM public.health_snapshots
                WHERE user_id = %s AND source = %s AND snapshot_date >= %s
                ORDER BY snapshot_date DESC
                """,
                (user_id, source, cutoff),
            )
        else:
            cur.execute(
                """
                SELECT id, user_id, source, snapshot_date, steps, active_minutes,
                       calories, distance_km, sleep_hours, sleep_stages, activities,
                       created_at, updated_at
                FROM public.health_snapshots
                WHERE user_id = %s AND snapshot_date >= %s
                ORDER BY snapshot_date DESC
                """,
                (user_id, cutoff),
            )
        rows = cur.fetchall()
        result = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return result
    except Exception as exc:
        log.warning("get_health_snapshots failed: %s", exc)
        return []
    finally:
        conn.close()


def purge_old_health_snapshots() -> int:
    """Delete health_snapshots older than 8 days. Returns count of deleted rows."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cutoff = date.today() - timedelta(days=8)
        cur.execute(
            "DELETE FROM public.health_snapshots WHERE snapshot_date < %s",
            (cutoff,),
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        log.info("Purged %d health snapshots older than %s", deleted, cutoff)
        return deleted
    except Exception as exc:
        log.warning("purge_old_health_snapshots failed: %s", exc)
        conn.rollback()
        return 0
    finally:
        conn.close()


# ── Google Fit sync ──────────────────────────────────────────────────────────

def sync_google_fit_for_user(user_id: str, target_date: Optional[date] = None) -> Dict:
    """Fetch Google Fit data for target_date and store in Supabase."""
    target = target_date or date.today()
    try:
        gfit = _get_google_fit()
        start_dt = datetime.combine(target, datetime.min.time())
        end_dt = datetime.combine(target, datetime.max.time())
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        raw = gfit.fetch_all_data(start_ms, end_ms)

        ok = upsert_health_snapshot(
            user_id=user_id,
            source="google_fit",
            snapshot_date=target,
            data=raw,
        )
        return {
            "ok": ok,
            "source": "google_fit",
            "snapshot_date": target.isoformat(),
            "detail": "Google Fit synced" if ok else "DB upsert failed",
        }
    except FileNotFoundError as exc:
        return {"ok": False, "source": "google_fit", "detail": str(exc)}
    except Exception as exc:
        log.error("Google Fit sync failed: %s", exc)
        return {"ok": False, "source": "google_fit", "detail": str(exc)}


# ── Strava sync ──────────────────────────────────────────────────────────────

def sync_strava_for_user(user_id: str, target_date: Optional[date] = None) -> Dict:
    """Fetch Strava data for target_date and store in Supabase."""
    target = target_date or date.today()
    if not _is_strava_configured():
        return {"ok": False, "source": "strava", "detail": "Strava not configured"}

    try:
        from ..api.strava_api import fetch_all_strava_data

        start_dt = datetime.combine(target, datetime.min.time())
        end_dt = datetime.combine(target, datetime.max.time())
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        raw = fetch_all_strava_data(start_ms, end_ms)

        summary = raw.get("summary", {})
        snapshot_data = {
            "steps": None,
            "active_minutes": int(summary.get("total_duration_min", 0)),
            "calories": summary.get("total_calories"),
            "distance_km": summary.get("total_distance_km"),
            "sleep_hours": None,
            "activities": raw.get("activities", []),
        }

        ok = upsert_health_snapshot(
            user_id=user_id,
            source="strava",
            snapshot_date=target,
            data=snapshot_data,
        )
        return {
            "ok": ok,
            "source": "strava",
            "snapshot_date": target.isoformat(),
            "detail": "Strava synced" if ok else "DB upsert failed",
        }
    except Exception as exc:
        log.error("Strava sync failed: %s", exc)
        return {"ok": False, "source": "strava", "detail": str(exc)}


def sync_health_for_user(user_id: str) -> Dict:
    """Sync both Google Fit + Strava for a user. Called by data_sync."""
    gfit_result = sync_google_fit_for_user(user_id)
    strava_result = sync_strava_for_user(user_id)
    return {
        "ok": gfit_result.get("ok", False) or strava_result.get("ok", False),
        "google_fit": gfit_result,
        "strava": strava_result,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

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
            sleep_stages=r.get("sleep_stages"),
            activities=r.get("activities"),
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
        )
        for r in rows
    ]


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
