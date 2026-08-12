"""Health feature service (NUMA-116 P4, PLAN 2.1 / 5.2 / 21.1).

`HealthService` owns the orchestration that used to sit inside the HTTP routes:
the status roll-up, snapshot listing and its DTO shaping, the intraday read with
its empty-window fallback, the three sync entrypoints, the agent chat call and
the purge job. Dependencies (persistence readers, sync callables, timezone
resolver, agent entrypoint) are injected through the constructor.

The LangGraph sub-agent moved to `agent.py`; its public entrypoint is re-exported
here so `master_agent.orchestrator` keeps its existing import path.

Errors: methods raise `core.errors.AppError` with the status code the route used
to raise directly; `router._http_error` maps them back to HTTP.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from ..core.base import BaseService
from ..core.errors import AppError
from .agent import (  # noqa: F401  re-exported for existing import paths
    HEALTH_AGENT_SYSTEM_PROMPT,
    HealthAgentState,
    run_health_agent_chat,
)
from .persistence import (
    get_health_intraday_snapshot,
    get_health_snapshots,
    purge_old_health_snapshots,
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

DEFAULT_SNAPSHOT_DAYS = 8
INTRADAY_BUCKET_MINUTES = 60
INTRADAY_SOURCE = "google_fit"

_SNAPSHOT_METRIC_KEYS = (
    "steps",
    "active_minutes",
    "calories",
    "distance_km",
    "sleep_hours",
    "heart_rate_bpm",
    "heart_points",
    "sleep_start_at",
    "sleep_end_at",
    "sleep_stages",
    "sleep_segments",
    "activities",
    "created_at",
    "updated_at",
)


class HealthService(BaseService):
    """Health data orchestration behind the /health-agent routes."""

    def __init__(
        self,
        read_snapshots: Optional[Callable[..., List[Dict]]] = None,
        read_intraday: Optional[Callable[..., Optional[Dict]]] = None,
        purge_snapshots: Optional[Callable[[], int]] = None,
        sync_google_fit: Optional[Callable[..., Dict]] = None,
        sync_strava: Optional[Callable[..., Dict]] = None,
        sync_all: Optional[Callable[[str], Dict]] = None,
        user_timezone: Optional[Callable[[str], ZoneInfo]] = None,
        chat_agent: Optional[Callable[..., Dict]] = None,
    ) -> None:
        super().__init__()
        self.read_snapshots = read_snapshots or get_health_snapshots
        self.read_intraday = read_intraday or get_health_intraday_snapshot
        self.purge_snapshots = purge_snapshots or purge_old_health_snapshots
        self.sync_google_fit_api = sync_google_fit or sync_google_fit_for_user
        self.sync_strava_api = sync_strava or sync_strava_for_user
        self.sync_all_api = sync_all or sync_health_for_user
        self.user_timezone = user_timezone or _get_user_timezone
        self.chat_agent = chat_agent or run_health_agent_chat

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self, user_id: Optional[str]) -> Dict:
        """Provider config plus today's snapshot counts.

        A missing user id yields empty counts rather than an error, exactly as
        the route did before.
        """
        snapshots = self.read_snapshots(user_id, days=DEFAULT_SNAPSHOT_DAYS) if user_id else []
        today = date.today()
        return {
            "google_fit_configured": _is_google_fit_configured(),
            "strava_configured": _is_strava_configured(),
            "snapshots_today": sum(1 for s in snapshots if s.get("snapshot_date") == today),
            "total_snapshots": len(snapshots),
        }

    # ── Snapshots ────────────────────────────────────────────────────────────

    def list_snapshots(
        self,
        user_id: str,
        source: Optional[str] = None,
        days: int = DEFAULT_SNAPSHOT_DAYS,
    ) -> List[Dict]:
        """Recent snapshots shaped for `HealthSnapshotOut` (no extra columns)."""
        rows = self.read_snapshots(user_id, source=source, days=days)
        return [self._snapshot_dto(row) for row in rows]

    @staticmethod
    def _snapshot_dto(row: Dict) -> Dict:
        dto = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "source": row["source"],
            "snapshot_date": row["snapshot_date"],
        }
        dto.update({key: row.get(key) for key in _SNAPSHOT_METRIC_KEYS})
        return dto

    # ── Intraday ─────────────────────────────────────────────────────────────

    def get_intraday(
        self,
        user_id: str,
        snapshot_date: date,
        source: str = INTRADAY_SOURCE,
    ) -> Dict:
        """Hourly buckets for one day, or a zero-filled window when none exist."""
        if source != INTRADAY_SOURCE:
            raise AppError(
                "Intraday health data is currently available for Google Fit only",
                status_code=400,
            )

        tz = self.user_timezone(user_id)
        row = self.read_intraday(user_id, snapshot_date=snapshot_date, source=source)
        if not row:
            window_start_at, window_end_at = _intraday_bounds(snapshot_date, tz)
            return {
                "id": None,
                "user_id": user_id,
                "source": source,
                "snapshot_date": snapshot_date,
                "window_start_at": window_start_at,
                "window_end_at": window_end_at,
                "bucket_minutes": INTRADAY_BUCKET_MINUTES,
                "steps": 0,
                "calories": 0,
                "distance_km": 0,
                "buckets": [
                    _bucket_for_api(bucket, tz)
                    for bucket in _empty_intraday_buckets(window_start_at, window_end_at)
                ],
            }

        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "source": row["source"],
            "snapshot_date": row["snapshot_date"],
            "window_start_at": row["window_start_at"],
            "window_end_at": row["window_end_at"],
            "bucket_minutes": row["bucket_minutes"],
            "steps": row.get("steps") or 0,
            "calories": row.get("calories") or 0,
            "distance_km": row.get("distance_km") or 0,
            "buckets": [_bucket_for_api(bucket, tz) for bucket in (row.get("buckets") or [])],
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    # ── Sync ─────────────────────────────────────────────────────────────────

    def sync_google_fit(self, user_id: str, target_date: Optional[date] = None) -> Dict:
        return self.sync_google_fit_api(user_id, target_date=target_date)

    def sync_strava(self, user_id: str, target_date: Optional[date] = None) -> Dict:
        return self.sync_strava_api(user_id, target_date=target_date)

    def sync_all(self, user_id: str) -> Dict:
        return self.sync_all_api(user_id)

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat(
        self,
        query: str,
        history: List[dict],
        user_id: Optional[str],
        model: Optional[str] = None,
    ) -> Dict:
        return self.chat_agent(query=query, history=history, user_id=user_id, model=model)

    # ── Maintenance ──────────────────────────────────────────────────────────

    def purge_old_snapshots(self) -> Dict:
        """Called by the APScheduler daily 8 AM job."""
        return {"ok": True, "deleted": self.purge_snapshots()}


health_service = HealthService()
