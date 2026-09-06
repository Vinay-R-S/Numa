"""Dashboard business logic (NUMA-113 P4, PLAN 2.1 / 5.2 / 21.1).

Aggregation, streak math and the weekly activity fill were extracted verbatim
from `router.py`, which is now HTTP-only. Query semantics are unchanged: this is
a pure move plus constructor injection of the repository.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..core.base import BaseService
from ..core.timezones import user_timezone
from .repository import DashboardRepository, dashboard_repository

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

WEEKLY_WINDOW_DAYS = 7

# Today can hold one snapshot per source. Cumulative metrics add up across
# sources; point-in-time metrics take the highest reported value.
HEALTH_METRICS: tuple[tuple[str, str], ...] = (
    ("steps", "sum"),
    ("active_minutes", "sum"),
    ("calories", "sum"),
    ("sleep_hours", "max"),
    ("distance_km", "max"),
    ("heart_rate_bpm", "max"),
    ("heart_points", "sum"),
)


def _local_date_key(value: date) -> str:
    return value.isoformat()


def _streak_from_dates(dates: list, today: date) -> int:
    """Count consecutive days back from today in a DESC-sorted date list."""
    streak = 0
    check = today
    for d in dates:
        if d != check:
            break
        streak += 1
        check -= timedelta(days=1)
    return streak


def _isoformat_in_place(rows: list, keys: tuple[str, ...]) -> None:
    for row in rows:
        for key in keys:
            if isinstance(row.get(key), (datetime, date)):
                row[key] = row[key].isoformat()


class DashboardService(BaseService):
    """Unified stats aggregation across all NUMA sub-agents."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        super().__init__()
        self.repository = repository or dashboard_repository

    def get_stats(self, user_id: str) -> dict:
        now_utc = datetime.now(timezone.utc)
        # One definition of the user's day. This paired a server-local `today`
        # with a UTC midnight and the database session's own `DATE()`, so both
        # streaks broke for any user not on UTC (NUMA-142 P6, PLAN 7).
        tz = user_timezone(user_id)
        today = datetime.now(tz).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=tz)

        raw = self.repository.fetch_stats_raw(
            user_id, today, today_start, now_utc, tz_name=str(tz),
        )

        recent_tasks = raw["recent_tasks"]
        _isoformat_in_place(recent_tasks, ("due_date", "created_at"))

        upcoming_events = raw["upcoming_events"]
        _isoformat_in_place(upcoming_events, ("start_at", "end_at"))

        github_row = raw["github_row"]
        journal_today = raw["journal_today"]

        return {
            "tasks": {
                "total": raw["total_tasks"],
                "completed": raw["completed_tasks"],
                "inprogress": raw["inprogress_tasks"],
                "pending": raw["pending_tasks"],
                "today": {
                    "total": (
                        raw["today_completed_tasks"]
                        + raw["today_inprogress_tasks"]
                        + raw["today_pending_tasks"]
                    ),
                    "completed": raw["today_completed_tasks"],
                    "inprogress": raw["today_inprogress_tasks"],
                    "pending": raw["today_pending_tasks"],
                },
                "streak": _streak_from_dates(raw["task_completed_dates"], today),
                "recent": recent_tasks,
            },
            "calendar": {
                "today_events": raw["today_events"],
                "upcoming": upcoming_events,
            },
            "slack": {
                "messages_7d": raw["slack_messages_7d"],
                "active_channels": raw["slack_channels"],
            },
            "health": self._summarize_health(raw["health_today"]),
            "health_weekly": self._weekly_activity(raw["health_weekly_rows"], today),
            "github": {
                "connected": len(github_row) > 0,
                "username": github_row[0]["github_username"] if github_row else None,
            },
            "journal": {
                "has_today": len(journal_today) > 0,
                "today_mood": journal_today[0]["mood"] if journal_today else None,
                "streak": _streak_from_dates(raw["journal_dates"], today),
            },
        }

    @staticmethod
    def _summarize_health(snapshots: list) -> dict:
        """Roll today's per-source snapshots into one set of metrics."""
        summary: dict = {}
        for snapshot in snapshots:
            for metric, mode in HEALTH_METRICS:
                value = snapshot.get(metric)
                if not value:
                    continue
                current = summary.get(metric) or 0
                summary[metric] = current + value if mode == "sum" else max(current, value)
        return summary

    @staticmethod
    def _weekly_activity(rows: list, today: date) -> list[dict]:
        """One entry per day for the last week, zero-filled where no snapshot exists."""
        by_date = {
            _local_date_key(row["snapshot_date"]): row
            for row in rows
            if row.get("snapshot_date")
        }
        weekly = []
        for offset in range(WEEKLY_WINDOW_DAYS - 1, -1, -1):
            day = today - timedelta(days=offset)
            row = by_date.get(_local_date_key(day), {})
            weekly.append(
                {
                    "date": _local_date_key(day),
                    "label": DAY_NAMES[day.weekday()],
                    "steps": row.get("steps") or 0,
                    "calories": row.get("calories") or 0,
                    "distance_km": row.get("distance_km") or 0,
                }
            )
        return weekly


dashboard_service = DashboardService()
