"""Health snapshot persistence (NUMA-108 P3, PLAN 16.6).

Write/read orchestration over ``HealthRepository`` plus the Qdrant vector
mirror. Keeps the router's original wrapper semantics (return-bool /
swallow-to-None-or-[] / log) so behavior is identical; raw SQL stays in
``repository.py``.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from ..memory import memory_service
from .repository import health_repository
from .utils import _dt_from_millis

log = logging.getLogger(__name__)


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
    try:
        health_repository.upsert_snapshot(
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
            _dt_from_millis(data.get("sleep_start_ms")),
            _dt_from_millis(data.get("sleep_end_ms")),
            json.dumps(data.get("sleep_stages")) if data.get("sleep_stages") else None,
            json.dumps(data.get("sleep_segments")) if data.get("sleep_segments") else None,
            json.dumps(data.get("activities")) if data.get("activities") else None,
        )
    except Exception as exc:
        log.warning("upsert_health_snapshot failed: %s", exc)
        return False
    _store_health_snapshot_vector(user_id, source, snapshot_date, data)
    return True


def delete_health_snapshot(user_id: str, source: str, snapshot_date: date) -> None:
    try:
        health_repository.delete_snapshot(user_id, source, snapshot_date)
    except Exception as exc:
        log.warning("delete_health_snapshot failed: %s", exc)


def upsert_health_intraday_snapshot(
    user_id: str,
    source: str,
    snapshot_date: date,
    window_start_at: datetime,
    window_end_at: datetime,
    buckets: List[Dict],
    bucket_minutes: int = 60,
) -> bool:
    steps = sum(int(bucket.get("steps") or 0) for bucket in buckets)
    calories = sum(int(bucket.get("calories") or 0) for bucket in buckets)
    distance_km = round(sum(float(bucket.get("distance_km") or 0) for bucket in buckets), 2)
    try:
        health_repository.upsert_intraday(
            user_id,
            source,
            snapshot_date,
            window_start_at,
            window_end_at,
            bucket_minutes,
            steps,
            calories,
            distance_km,
            json.dumps(buckets),
        )
        return True
    except Exception as exc:
        log.warning("upsert_health_intraday_snapshot failed: %s", exc)
        return False


def get_health_intraday_snapshot(
    user_id: str,
    snapshot_date: date,
    source: str = "google_fit",
    bucket_minutes: int = 60,
) -> Optional[Dict]:
    try:
        return health_repository.get_intraday(user_id, snapshot_date, source, bucket_minutes)
    except Exception as exc:
        log.warning("get_health_intraday_snapshot failed: %s", exc)
        return None


def get_health_snapshots(
    user_id: str,
    source: Optional[str] = None,
    days: int = 8,
) -> List[Dict]:
    """Fetch recent health snapshots for a user (up to N days)."""
    try:
        cutoff = date.today() - timedelta(days=days)
        return health_repository.get_snapshots(user_id, source, cutoff)
    except Exception as exc:
        log.warning("get_health_snapshots failed: %s", exc)
        return []


def purge_old_health_snapshots() -> int:
    """Delete health rows older than 8 days. Returns count of deleted rows."""
    try:
        cutoff = date.today() - timedelta(days=8)
        deleted = health_repository.purge_older_than(cutoff)
        log.info("Purged %d health snapshots older than %s", deleted, cutoff)
        return deleted
    except Exception as exc:
        log.warning("purge_old_health_snapshots failed: %s", exc)
        return 0
