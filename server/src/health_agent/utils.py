"""Health helpers: timezone resolution, time/bucket math (NUMA-108 P3, PLAN 16.6).

Pure functions only - no DB, no external API, no memory. Extracted from the
health router god-file so both the router and the sync layer can share them.
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _resolve_timezone_name(name: Optional[str]) -> ZoneInfo:
    fallback = os.getenv("TIMEZONE", "Asia/Kolkata")
    for candidate in (name, fallback, "UTC"):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except ZoneInfoNotFoundError:
            continue
    return ZoneInfo("UTC")


def _millis(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _dt_from_millis(value: Optional[int]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc)


def _activity_day_bounds(target: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def _sleep_night_bounds(target: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(target - timedelta(days=1), time(18, 0), tzinfo=tz)
    end = datetime.combine(target, time(12, 0), tzinfo=tz)
    return start, end


def _intraday_bounds(target: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time(6, 0), tzinfo=tz)
    end = datetime.combine(target, time(22, 0), tzinfo=tz)
    return start, end


def _bucket_for_api(bucket: Dict, tz: ZoneInfo) -> Dict:
    start_ms = bucket.get("start_ms")
    end_ms = bucket.get("end_ms")
    start_dt = _dt_from_millis(start_ms)
    end_dt = _dt_from_millis(end_ms)
    local_start = start_dt.astimezone(tz) if start_dt else None
    local_end = end_dt.astimezone(tz) if end_dt else None
    return {
        "bucket_start_at": start_dt,
        "bucket_end_at": end_dt,
        "label": local_start.strftime("%H:%M") if local_start else "",
        "range_label": (
            f"{local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')}"
            if local_start and local_end else ""
        ),
        "steps": bucket.get("steps") or 0,
        "calories": bucket.get("calories") or 0,
        "distance_km": bucket.get("distance_km") or 0,
    }


def _empty_intraday_buckets(window_start_at: datetime, window_end_at: datetime, bucket_minutes: int = 60) -> List[Dict]:
    buckets = []
    current = window_start_at
    while current < window_end_at:
        bucket_end = min(current + timedelta(minutes=bucket_minutes), window_end_at)
        buckets.append({
            "start_ms": _millis(current),
            "end_ms": _millis(bucket_end),
            "steps": 0,
            "calories": 0,
            "distance_km": 0,
        })
        current = bucket_end
    return buckets


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
