"""Health provider sync orchestration (NUMA-108 P3, PLAN 16.6).

Config detection, the lazy Google Fit client, transient/not-connected error
classifiers, and the Google Fit / Strava / combined sync entrypoints. Persists
through ``persistence.py``; contains no SQL and no HTTP route code.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from .persistence import (
    delete_health_snapshot,
    upsert_health_intraday_snapshot,
    upsert_health_snapshot,
)
from .repository import health_repository
from .utils import (
    _activity_day_bounds,
    _has_health_values,
    _intraday_bounds,
    _millis,
    _resolve_timezone_name,
    _sleep_night_bounds,
)

log = logging.getLogger(__name__)

# Google Fit API (lazy singleton, per user)
_google_fit_instances: Dict[str, object] = {}
_google_fit_instances_lock = threading.Lock()


def _get_user_timezone(user_id: str) -> ZoneInfo:
    try:
        return _resolve_timezone_name(health_repository.timezone_name(user_id))
    except Exception as exc:
        log.debug("Falling back to default timezone for health sync: %s", exc)
        return _resolve_timezone_name(None)


def _get_google_fit(user_id: str):
    """Lazy-init Google Fit API client."""
    if user_id not in _google_fit_instances:
        with _google_fit_instances_lock:
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
    "wrong_version_number",
    "[ssl] internal error",
    "ssl: internal error",
    "internal error (_ssl",
    "decryption_failed_or_bad_record_mac",
    "bad record mac",
    "eof occurred in violation of protocol",
    "transient google fit api",
    "timed out",
    "timeout",
)


def _is_transient_sync_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_SYNC_ERROR_MARKERS)


def _is_google_fit_not_connected_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "google fit is not connected",
            "google calendar is not connected",
            "start oauth",
            "please reconnect",
            "reconnect google",
            "session expired",
            "missing newly required scopes",
            "insufficient authentication scopes",
            "access_token_scope_insufficient",
        )
    )


def _sync_temporarily_unavailable_detail(source: str) -> str:
    return f"{source} temporarily unavailable; sync skipped"


def sync_google_fit_for_user(user_id: str, target_date: Optional[date] = None) -> Dict:
    """Fetch Google Fit data for target_date and store in Supabase."""
    target = target_date or date.today()
    try:
        gfit = _get_google_fit(user_id)
        tz = _get_user_timezone(user_id)
        start_dt, end_dt = _activity_day_bounds(target, tz)
        start_ms = _millis(start_dt)
        end_ms = _millis(end_dt)

        raw = gfit.fetch_all_data(start_ms, end_ms, include_sleep=False)
        sleep_start_dt, sleep_end_dt = _sleep_night_bounds(target, tz)
        sleep_result = None
        sleep_error = None
        try:
            sleep_result = gfit.fetch_sleep(_millis(sleep_start_dt), _millis(sleep_end_dt))
        except Exception as exc:
            sleep_error = str(exc)
            log.warning("Google Fit sleep fetch failed for %s: %s", target.isoformat(), exc)
        if sleep_result:
            raw["sleep_hours"] = sleep_result.get("hours")
            raw["sleep_start_ms"] = sleep_result.get("start_ms")
            raw["sleep_end_ms"] = sleep_result.get("end_ms")
            raw["sleep_stages"] = sleep_result.get("stages")
            raw["sleep_segments"] = sleep_result.get("segments")

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
        intraday_saved = False
        try:
            intraday_start_dt, intraday_end_dt = _intraday_bounds(target, tz)
            intraday_buckets = gfit.fetch_intraday_activity(
                _millis(intraday_start_dt),
                _millis(intraday_end_dt),
                bucket_minutes=60,
            )
            if intraday_buckets:
                intraday_saved = upsert_health_intraday_snapshot(
                    user_id=user_id,
                    source="google_fit",
                    snapshot_date=target,
                    window_start_at=intraday_start_dt,
                    window_end_at=intraday_end_dt,
                    buckets=intraday_buckets,
                    bucket_minutes=60,
                )
        except Exception as exc:
            log.warning("Google Fit intraday fetch failed for %s: %s", target.isoformat(), exc)
        detail_parts = ["Google Fit synced" if ok else "DB upsert failed"]
        detail_parts.append(f"sleep={'yes' if sleep_result else 'no'}")
        detail_parts.append(f"hourly={'yes' if intraday_saved else 'no'}")
        if sleep_error:
            detail_parts.append(f"sleep_error={sleep_error[:120]}")
        return {
            "ok": ok,
            "source": "google_fit",
            "snapshot_date": target.isoformat(),
            "detail": " | ".join(detail_parts),
            "sleep_synced": bool(sleep_result),
            "hourly_synced": bool(intraday_saved),
        }
    except FileNotFoundError as exc:
        return {"ok": False, "source": "google_fit", "detail": str(exc)}
    except Exception as exc:
        if _is_google_fit_not_connected_error(exc):
            log.debug("Google Fit sync skipped for user %s: %s", user_id, exc)
            return {
                "ok": False,
                "source": "google_fit",
                "snapshot_date": target.isoformat(),
                "detail": str(exc),
                "not_connected": True,
            }
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
            if gfit_result.get("transient") or gfit_result.get("not_connected"):
                gfit_unavailable = True
        if sync_strava:
            strava_results.append(sync_strava_for_user(user_id, target_date=target))

    gfit_ok = sum(1 for result in gfit_results if result.get("ok"))
    gfit_sleep_ok = sum(1 for result in gfit_results if result.get("sleep_synced"))
    gfit_hourly_ok = sum(1 for result in gfit_results if result.get("hourly_synced"))
    strava_ok = sum(1 for result in strava_results if result.get("ok"))
    details = []
    if gfit_ok:
        details.append(
            f"Google Fit synced {gfit_ok}/{days} days"
            f" (sleep {gfit_sleep_ok}/{days}, hourly {gfit_hourly_ok}/{days})"
        )
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
        "not_connected": bool(gfit_results and gfit_results[0].get("not_connected")),
    }
