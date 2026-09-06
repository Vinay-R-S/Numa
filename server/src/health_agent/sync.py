"""Health provider sync orchestration (NUMA-108 P3, PLAN 16.6).

Config detection, the lazy Google Fit client, transient/not-connected error
classifiers, and the Google Fit / Strava / combined sync entrypoints. Persists
through ``persistence.py``; contains no SQL and no HTTP route code.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
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
    HEALTH_RETENTION_DAYS,
    _activity_day_bounds,
    _has_health_values,
    _intraday_bounds,
    _millis,
    _resolve_timezone_name,
    _sleep_night_bounds,
)

log = logging.getLogger(__name__)

# Google Fit API (lazy singleton, per user). Bounded: this was an unevicted
# dict holding one client, its credentials and its HTTP session for every user
# the process ever synced (NUMA-142 P6, PLAN 9).
_GOOGLE_FIT_CACHE_MAX = 128
_google_fit_instances: "OrderedDict[str, object]" = OrderedDict()
_google_fit_instances_lock = threading.Lock()

# The periodic sync used to re-fetch all 8 days on every tick: 8 days times
# several Google Fit calls each, per user, every 30 minutes. Days that have
# already closed only change when a provider backfills them, so the full window
# runs twice a day and the ticks in between cover the days still moving.
_FULL_BACKFILL_INTERVAL_SECONDS = 12 * 3600
_RECENT_SYNC_DAYS = 2
_BACKFILL_TRACK_MAX = 1024
_last_full_backfill: Dict[str, float] = {}
_backfill_lock = threading.Lock()


def _days_to_sync(user_id: str) -> int:
    """How many days this tick should cover: the recent window, or the lot."""
    now = time.time()
    with _backfill_lock:
        last = _last_full_backfill.get(user_id, 0.0)
        if now - last < _FULL_BACKFILL_INTERVAL_SECONDS:
            return _RECENT_SYNC_DAYS
        return HEALTH_RETENTION_DAYS


def _record_full_backfill(user_id: str) -> None:
    """Mark a full backfill done, once it actually succeeded.

    Stamping this before the sync ran meant a failed backfill (an expired token,
    a Google Fit 5xx) was not retried for twelve hours and the gap silently
    stayed (NUMA-142 P6 review).
    """
    with _backfill_lock:
        if len(_last_full_backfill) >= _BACKFILL_TRACK_MAX:
            _last_full_backfill.clear()
        _last_full_backfill[user_id] = time.time()


def _get_user_timezone(user_id: str) -> ZoneInfo:
    try:
        return _resolve_timezone_name(health_repository.timezone_name(user_id))
    except Exception as exc:
        log.debug("Falling back to default timezone for health sync: %s", exc)
        return _resolve_timezone_name(None)


def _get_google_fit(user_id: str):
    """Lazy-init Google Fit API client, kept in a bounded LRU."""
    with _google_fit_instances_lock:
        client = _google_fit_instances.get(user_id)
        if client is not None:
            _google_fit_instances.move_to_end(user_id)
            return client

        from .google_fit_client import GoogleFitClient

        client = GoogleFitClient(user_id=user_id)
        _google_fit_instances[user_id] = client
        while len(_google_fit_instances) > _GOOGLE_FIT_CACHE_MAX:
            _google_fit_instances.popitem(last=False)
        return client


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
    # The user's today, not the host's. Fixing only the window left the day
    # itself host-local, so on a UTC host an IST user's current day was not
    # synced until UTC rolled over (NUMA-142 P6).
    tz = _get_user_timezone(user_id)
    target = target_date or datetime.now(tz).date()
    try:
        gfit = _get_google_fit(user_id)
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
    # The config check first: resolving the timezone reads public.profiles, and
    # doing it above this return cost one query per day per user on every tick
    # of a deployment with Strava switched off (NUMA-142 P6 review).
    if not _is_strava_configured():
        return {"ok": False, "source": "strava", "detail": "Strava not configured"}

    tz = _get_user_timezone(user_id)
    target = target_date or datetime.now(tz).date()

    try:
        from ..api.strava_api import StravaAPI

        # The user's timezone, not the host's. These were naive datetimes, so
        # the window was built in whatever zone the server happened to run in:
        # on a UTC host an IST user's 22:00 run was attributed to the next
        # snapshot_date, _has_health_values then saw an empty day, and
        # delete_health_snapshot wiped the row a previous sync had stored
        # correctly (NUMA-142 P6, PLAN 7). _activity_day_bounds also gives the
        # half-open [midnight, next midnight) window the Google Fit path uses,
        # rather than stopping at 23:59:59.999999.
        start_dt, end_dt = _activity_day_bounds(target, tz)
        start_ms = _millis(start_dt)
        end_ms = _millis(end_dt)

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


def sync_health_for_user(user_id: str, days: Optional[int] = None) -> Dict:
    """Sync recent health data for a user. Called by data_sync.

    `days` defaults to the recent window on a periodic tick and to the full
    retention window twice a day, rather than re-fetching all 8 days from every
    provider on every tick (NUMA-142 P6, PLAN 9).
    """
    requested_days = days
    days = days or _days_to_sync(user_id)
    tz = _get_user_timezone(user_id)
    today = datetime.now(tz).date()
    gfit_results = []
    strava_results = []
    sync_strava = _sync_strava_with_health_all()
    gfit_unavailable = False
    for offset in range(days):
        target = today - timedelta(days=offset)
        if not gfit_unavailable:
            gfit_result = sync_google_fit_for_user(user_id, target_date=target)
            gfit_results.append(gfit_result)
            if gfit_result.get("transient") or gfit_result.get("not_connected"):
                gfit_unavailable = True
        if sync_strava:
            strava_results.append(sync_strava_for_user(user_id, target_date=target))

    gfit_ok = sum(1 for result in gfit_results if result.get("ok"))
    strava_any_ok = any(result.get("ok") for result in strava_results)
    # Recorded only now, and only for a run that both asked for the full window
    # and got something back.
    if requested_days is None and days == HEALTH_RETENTION_DAYS and (gfit_ok or strava_any_ok):
        _record_full_backfill(user_id)

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
