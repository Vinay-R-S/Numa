"""Dashboard data-access layer (NUMA-113, PLAN 6/18/21). SQL only.

Runs every stats query on a single pooled connection (matching the previous
router behavior) and returns raw rows; all Python shaping stays in the router.
Per-query failures are swallowed to [] / default exactly as before.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict
from ..health_agent.repository import health_repository

log = logging.getLogger(__name__)


def _recover(conn, exc: Exception) -> None:
    """Roll the failed statement back so the next one can run.

    All 18 queries here share one pooled connection with autocommit off. Without
    this, the first failure left the connection in `InFailedSqlTransaction` and
    every remaining statement raised "current transaction is aborted" into these
    same handlers, so one broken query returned an entirely empty dashboard to a
    user with a full database (NUMA-142 P6, PLAN 7).
    """
    log.debug("Dashboard query failed: %s", exc)
    try:
        conn.rollback()
    except Exception:
        log.debug("Dashboard rollback after a failed query also failed", exc_info=True)


def _safe_call(conn, read):
    """Run a repository read with the same swallow-and-recover contract."""
    try:
        return read()
    except Exception as exc:
        _recover(conn, exc)
        return []


def _safe_query(conn, sql: str, params: tuple = ()) -> List[dict]:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        # `core.db.row_to_dict`, not a fourth hand-rolled copy of it (PLAN 10).
        mapped = [row_to_dict(cur, row) for row in rows]
        cur.close()
        return mapped
    except Exception as exc:
        _recover(conn, exc)
        return []


def _safe_scalar(conn, sql: str, params: tuple = (), default=0):
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row[0] if row else default
    except Exception as exc:
        _recover(conn, exc)
        return default


def _safe_date_list(conn, sql: str, params: tuple = ()) -> list:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = [r[0] for r in cur.fetchall()]
        cur.close()
        return result
    except Exception as exc:
        _recover(conn, exc)
        return []


class DashboardRepository(BaseRepository):
    def fetch_stats_raw(
        self, user_id: str, today: date, today_start: datetime, now_utc: datetime,
        tz_name: str = "UTC",
    ) -> Dict:
        day = timedelta(days=1)
        with get_db() as conn:
            total_tasks = _safe_scalar(
                conn, "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s", (user_id,)
            )
            completed_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s AND status = 'completed'",
                (user_id,),
            )
            pending_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s "
                "AND status IN ('planned', 'inprogress', 'pending')",
                (user_id,),
            )
            inprogress_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s AND status = 'inprogress'",
                (user_id,),
            )
            today_completed_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks "
                "WHERE user_id = %s AND status = 'completed' "
                "  AND completed_at >= %s AND completed_at < %s",
                (user_id, today_start, today_start + day),
            )
            today_inprogress_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks "
                "WHERE user_id = %s AND status = 'inprogress' "
                "  AND ((due_date >= %s AND due_date < %s) "
                "       OR (due_date IS NULL AND created_at >= %s AND created_at < %s))",
                (user_id, today_start, today_start + day, today_start, today_start + day),
            )
            today_pending_tasks = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.tasks "
                "WHERE user_id = %s AND status IN ('planned', 'pending') "
                "  AND ((due_date >= %s AND due_date < %s) "
                "       OR (due_date IS NULL AND created_at >= %s AND created_at < %s))",
                (user_id, today_start, today_start + day, today_start, today_start + day),
            )
            task_completed_dates = _safe_date_list(
                conn,
                # In the user's zone, so the days line up with the `today` the
                # streak counts back from. A bare DATE() used the database
                # session's zone (NUMA-142 P6, PLAN 7).
                "SELECT DISTINCT DATE(completed_at AT TIME ZONE %s) as d FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "ORDER BY d DESC LIMIT 30",
                (tz_name, user_id),
            )
            recent_tasks = _safe_query(
                conn,
                "SELECT title, status, priority, due_date, source_name, created_at "
                "FROM public.tasks WHERE user_id = %s "
                "ORDER BY updated_at DESC LIMIT 5",
                (user_id,),
            )
            today_events = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.cal_events "
                "WHERE user_id = %s AND start_at >= %s AND start_at < %s AND deleted_at IS NULL",
                (user_id, today_start, today_start + day),
            )
            upcoming_events = _safe_query(
                conn,
                "SELECT title, start_at, end_at FROM public.cal_events "
                "WHERE user_id = %s AND start_at >= %s AND deleted_at IS NULL "
                "ORDER BY start_at LIMIT 5",
                (user_id, now_utc),
            )
            slack_messages_7d = _safe_scalar(
                conn,
                "SELECT COUNT(*) FROM public.slack_messages "
                "WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days'",
                (user_id,),
            )
            slack_channels = _safe_scalar(
                conn,
                "SELECT COUNT(DISTINCT channel_name) FROM public.slack_messages "
                "WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days'",
                (user_id,),
            )
            # Through HealthRepository, on this batch's own connection, rather
            # than a fifth copy of the same SQL (NUMA-143 P7, PLAN 10). Wrapped
            # so one failing health query still cannot empty the dashboard.
            health_today = _safe_call(
                conn,
                lambda: health_repository.day_metrics(user_id, today, conn=conn),
            )
            health_weekly_rows = _safe_call(
                conn,
                lambda: health_repository.daily_totals_between(
                    user_id, "google_fit", today - timedelta(days=6), today, conn=conn,
                ),
            )
            github_row = _safe_query(
                conn,
                "SELECT github_username, avatar_url FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            journal_today = _safe_query(
                conn,
                "SELECT title, mood, ai_summary FROM public.journal_entries "
                "WHERE user_id = %s AND entry_date = %s",
                (user_id, today),
            )
            journal_dates = _safe_date_list(
                conn,
                "SELECT entry_date FROM public.journal_entries "
                "WHERE user_id = %s ORDER BY entry_date DESC LIMIT 30",
                (user_id,),
            )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "inprogress_tasks": inprogress_tasks,
            "today_completed_tasks": today_completed_tasks,
            "today_inprogress_tasks": today_inprogress_tasks,
            "today_pending_tasks": today_pending_tasks,
            "task_completed_dates": task_completed_dates,
            "recent_tasks": recent_tasks,
            "today_events": today_events,
            "upcoming_events": upcoming_events,
            "slack_messages_7d": slack_messages_7d,
            "slack_channels": slack_channels,
            "health_today": health_today,
            "health_weekly_rows": health_weekly_rows,
            "github_row": github_row,
            "journal_today": journal_today,
            "journal_dates": journal_dates,
        }


dashboard_repository = DashboardRepository()
