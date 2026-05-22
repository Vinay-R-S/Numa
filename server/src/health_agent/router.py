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

_google_fit_instances: Dict[str, object] = {}


def _get_google_fit(user_id: str):
    """Lazy-init Google Fit API client."""
    if user_id not in _google_fit_instances:
        from .google_fit_client import GoogleFitClient
        _google_fit_instances[user_id] = GoogleFitClient(user_id=user_id)
    return _google_fit_instances[user_id]


def _is_google_fit_configured() -> bool:
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    creds_file = os.getenv(
        'GOOGLE_FIT_CREDENTIALS_FILE',
        os.path.join(config_dir, 'credentials.json'),
    )
    if creds_file and not os.path.isabs(creds_file):
        creds_file = os.path.join(config_dir, creds_file)
    has_credentials_file = os.path.exists(creds_file)
    has_env_client = bool(
        os.getenv("GOOGLE_FIT_CLIENT_ID") and os.getenv("GOOGLE_FIT_CLIENT_SECRET")
    )
    return has_credentials_file or has_env_client


def _is_strava_configured() -> bool:
    return bool(
        (os.getenv("STRAVA_CLIENT_ID") or "").strip().strip("\"'")
        and (os.getenv("STRAVA_CLIENT_SECRET") or "").strip().strip("\"'")
        and (os.getenv("STRAVA_REFRESH_TOKEN") or "").strip().strip("\"'")
    )


def _sync_strava_with_health_all() -> bool:
    return (os.getenv("HEALTH_SYNC_STRAVA_WITH_ALL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


_TRANSIENT_SYNC_ERROR_MARKERS = (
    "getaddrinfo failed",
    "could not translate host name",
    "name or service not known",
    "temporary failure in name resolution",
    "unable to find the server",
    "server closed the connection unexpectedly",
    "connection unexpectedly",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
)


def _is_transient_sync_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_SYNC_ERROR_MARKERS)


def _sync_temporarily_unavailable_detail(source: str) -> str:
    return f"{source} temporarily unavailable; sync skipped"


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
            f"Heart rate bpm: {data.get('heart_rate_bpm') if data.get('heart_rate_bpm') is not None else 'unknown'}.\n"
            f"Heart points: {data.get('heart_points') if data.get('heart_points') is not None else 'unknown'}.\n"
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
                "heart_rate_bpm": data.get("heart_rate_bpm"),
                "heart_points": data.get("heart_points"),
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
                 distance_km, sleep_hours, heart_rate_bpm, heart_points,
                 sleep_stages, activities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, source, snapshot_date)
            DO UPDATE SET
                steps          = EXCLUDED.steps,
                active_minutes = EXCLUDED.active_minutes,
                calories       = EXCLUDED.calories,
                distance_km    = EXCLUDED.distance_km,
                sleep_hours    = EXCLUDED.sleep_hours,
                heart_rate_bpm = EXCLUDED.heart_rate_bpm,
                heart_points   = EXCLUDED.heart_points,
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
                data.get("heart_rate_bpm"),
                data.get("heart_points"),
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


def delete_health_snapshot(user_id: str, source: str, snapshot_date: date) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM public.health_snapshots
            WHERE user_id = %s AND source = %s AND snapshot_date = %s
            """,
            (user_id, source, snapshot_date),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("delete_health_snapshot failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()


def _has_health_values(data: Dict) -> bool:
    numeric_keys = (
        "steps",
        "active_minutes",
        "calories",
        "distance_km",
        "sleep_hours",
        "heart_rate_bpm",
        "heart_points",
    )
    if any((data.get(key) or 0) > 0 for key in numeric_keys):
        return True
    sleep_stages = data.get("sleep_stages")
    if isinstance(sleep_stages, dict) and any((value or 0) > 0 for value in sleep_stages.values()):
        return True
    activities = data.get("activities")
    if isinstance(activities, dict) and any((value or 0) > 0 for value in activities.values()):
        return True
    if isinstance(activities, list) and len(activities) > 0:
        return True
    return False


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
                       calories, distance_km, sleep_hours, heart_rate_bpm,
                       heart_points, sleep_stages, activities,
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
                       calories, distance_km, sleep_hours, heart_rate_bpm,
                       heart_points, sleep_stages, activities,
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
        gfit = _get_google_fit(user_id)
        start_dt = datetime.combine(target, datetime.min.time())
        end_dt = datetime.combine(target, datetime.max.time())
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        raw = gfit.fetch_all_data(start_ms, end_ms)
        if not _has_health_values(raw):
            delete_health_snapshot(user_id, "google_fit", target)
            return {
                "ok": False,
                "source": "google_fit",
                "snapshot_date": target.isoformat(),
                "detail": "Google Fit returned no health data for this date. Make sure the Google account that owns the Fit data completed OAuth.",
            }

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
        if _is_transient_sync_error(exc):
            log.debug("Google Fit sync skipped: %s", exc)
            return {
                "ok": False,
                "source": "google_fit",
                "snapshot_date": target.isoformat(),
                "detail": _sync_temporarily_unavailable_detail("Google Fit"),
                "transient": True,
            }
        log.error("Google Fit sync failed: %s", exc)
        return {"ok": False, "source": "google_fit", "snapshot_date": target.isoformat(), "detail": str(exc)}


# ── Strava sync ──────────────────────────────────────────────────────────────

def sync_strava_for_user(user_id: str, target_date: Optional[date] = None) -> Dict:
    """Fetch Strava data for target_date and store in Supabase."""
    target = target_date or date.today()
    if not _is_strava_configured():
        return {"ok": False, "source": "strava", "detail": "Strava not configured"}

    try:
        from ..api.strava_api import StravaAPI

        start_dt = datetime.combine(target, datetime.min.time())
        end_dt = datetime.combine(target, datetime.max.time())
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        raw = StravaAPI().fetch_all_data(start_ms, end_ms)

        summary = raw.get("summary", {})
        snapshot_data = {
            "steps": None,
            "active_minutes": int(summary.get("total_duration_min", 0)),
            "calories": summary.get("total_calories"),
            "distance_km": summary.get("total_distance_km"),
            "sleep_hours": None,
            "heart_rate_bpm": None,
            "heart_points": None,
            "activities": raw.get("activities", []),
        }
        if not _has_health_values(snapshot_data):
            delete_health_snapshot(user_id, "strava", target)
            return {
                "ok": False,
                "source": "strava",
                "snapshot_date": target.isoformat(),
                "detail": "Strava returned no activities for this date.",
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
    """Sync recent health data for a user. Called by data_sync."""
    days = 8
    gfit_results = []
    strava_results = []
    sync_strava = _sync_strava_with_health_all()
    gfit_unavailable = False
    for offset in range(days):
        target = date.today() - timedelta(days=offset)
        if not gfit_unavailable:
            gfit_result = sync_google_fit_for_user(user_id, target_date=target)
            gfit_results.append(gfit_result)
            if gfit_result.get("transient"):
                gfit_unavailable = True
        if sync_strava:
            strava_results.append(sync_strava_for_user(user_id, target_date=target))

    gfit_ok = sum(1 for result in gfit_results if result.get("ok"))
    strava_ok = sum(1 for result in strava_results if result.get("ok"))
    details = []
    if gfit_ok:
        details.append(f"Google Fit synced {gfit_ok}/{days} days")
    else:
        details.append(gfit_results[0].get("detail") or "Google Fit returned no recent data")
    if sync_strava:
        if strava_ok:
            details.append(f"Strava synced {strava_ok}/{days} days")
        else:
            details.append(strava_results[0].get("detail") or "Strava returned no recent data")
    else:
        details.append("Strava skipped")

    return {
        "ok": bool(gfit_ok or strava_ok),
        "detail": " | ".join(details),
        "google_fit": gfit_results,
        "strava": strava_results,
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
            heart_rate_bpm=r.get("heart_rate_bpm"),
            heart_points=r.get("heart_points"),
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
