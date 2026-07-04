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
from ..core.db import get_db

log = logging.getLogger(__name__)


def _safe_query(conn, sql: str, params: tuple = ()) -> List[dict]:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = cur.description
        cur.close()
        return [{col.name: val for col, val in zip(desc, row)} for row in rows]
    except Exception as exc:
        log.debug("Dashboard query failed: %s", exc)
        return []


def _safe_scalar(conn, sql: str, params: tuple = (), default=0):
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row[0] if row else default
    except Exception:
        return default


def _safe_date_list(conn, sql: str, params: tuple = ()) -> list:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = [r[0] for r in cur.fetchall()]
        cur.close()
        return result
    except Exception:
        return []


class DashboardRepository(BaseRepository):
    def fetch_stats_raw(
        self, user_id: str, today: date, today_start: datetime, now_utc: datetime
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
                "SELECT DISTINCT DATE(completed_at) as d FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "ORDER BY d DESC LIMIT 30",
                (user_id,),
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
            health_today = _safe_query(
                conn,
                "SELECT source, steps, active_minutes, calories, distance_km, sleep_hours, "
                "       heart_rate_bpm, heart_points "
                "FROM public.health_snapshots WHERE user_id = %s AND snapshot_date = %s",
                (user_id, today),
            )
            health_weekly_rows = _safe_query(
                conn,
                "SELECT snapshot_date, steps, calories, distance_km "
                "FROM public.health_snapshots "
                "WHERE user_id = %s AND source = 'google_fit' "
                "  AND snapshot_date >= %s AND snapshot_date <= %s "
                "ORDER BY snapshot_date",
                (user_id, today - timedelta(days=6), today),
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
