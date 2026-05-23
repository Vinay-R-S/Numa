"""
Dashboard Router - unified stats aggregation from all NUMA sub-agents.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_user
from ..db import _get_conn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _safe_query(conn, sql: str, params: tuple = ()) -> list:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = cur.description
        cur.close()
        return [
            {col.name: val for col, val in zip(desc, row)}
            for row in rows
        ]
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


def _local_date_key(value: date) -> str:
    return value.isoformat()


@router.get("/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    now_utc = datetime.now(timezone.utc)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=7)

    conn = _get_conn()
    try:
        # ── Tasks ──────────────────────────────────────────────────────────
        total_tasks = _safe_scalar(conn, "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s", (user_id,))
        completed_tasks = _safe_scalar(
            conn,
            "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s AND status = 'completed'",
            (user_id,),
        )
        pending_tasks = _safe_scalar(
            conn,
            "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s AND status IN ('planned', 'inprogress', 'pending')",
            (user_id,),
        )
        inprogress_tasks = _safe_scalar(
            conn,
            "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s AND status = 'inprogress'",
            (user_id,),
        )
        today_completed_tasks = _safe_scalar(
            conn,
            """
            SELECT COUNT(*) FROM public.tasks
            WHERE user_id = %s
              AND status = 'completed'
              AND completed_at >= %s
              AND completed_at < %s
            """,
            (user_id, today_start, today_start + timedelta(days=1)),
        )
        today_inprogress_tasks = _safe_scalar(
            conn,
            """
            SELECT COUNT(*) FROM public.tasks
            WHERE user_id = %s
              AND status = 'inprogress'
              AND (
                (due_date >= %s AND due_date < %s)
                OR (due_date IS NULL AND created_at >= %s AND created_at < %s)
              )
            """,
            (user_id, today_start, today_start + timedelta(days=1), today_start, today_start + timedelta(days=1)),
        )
        today_pending_tasks = _safe_scalar(
            conn,
            """
            SELECT COUNT(*) FROM public.tasks
            WHERE user_id = %s
              AND status IN ('planned', 'pending')
              AND (
                (due_date >= %s AND due_date < %s)
                OR (due_date IS NULL AND created_at >= %s AND created_at < %s)
              )
            """,
            (user_id, today_start, today_start + timedelta(days=1), today_start, today_start + timedelta(days=1)),
        )

        task_streak = 0
        try:
            cur2 = conn.cursor()
            cur2.execute(
                """
                SELECT DISTINCT DATE(completed_at) as d FROM public.tasks
                WHERE user_id = %s AND completed_at IS NOT NULL
                ORDER BY d DESC LIMIT 30
                """,
                (user_id,),
            )
            check_date = today
            for (d,) in cur2.fetchall():
                if d == check_date:
                    task_streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break
            cur2.close()
        except Exception:
            pass

        recent_tasks = _safe_query(
            conn,
            """
            SELECT title, status, priority, due_date, source_name, created_at
            FROM public.tasks WHERE user_id = %s
            ORDER BY updated_at DESC LIMIT 5
            """,
            (user_id,),
        )
        for t in recent_tasks:
            for k in ("due_date", "created_at"):
                if isinstance(t.get(k), (datetime, date)):
                    t[k] = t[k].isoformat()

        # ── Calendar ───────────────────────────────────────────────────────
        today_events = _safe_scalar(
            conn,
            """
            SELECT COUNT(*) FROM public.cal_events
            WHERE user_id = %s AND start_at >= %s AND start_at < %s AND deleted_at IS NULL
            """,
            (user_id, today_start, today_start + timedelta(days=1)),
        )
        upcoming_events = _safe_query(
            conn,
            """
            SELECT title, start_at, end_at FROM public.cal_events
            WHERE user_id = %s AND start_at >= %s AND deleted_at IS NULL
            ORDER BY start_at LIMIT 5
            """,
            (user_id, now_utc),
        )
        for e in upcoming_events:
            for k in ("start_at", "end_at"):
                if isinstance(e.get(k), datetime):
                    e[k] = e[k].isoformat()

        # ── Slack ──────────────────────────────────────────────────────────
        slack_messages_7d = _safe_scalar(
            conn,
            """
            SELECT COUNT(*) FROM public.slack_messages
            WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days'
            """,
            (user_id,),
        )
        slack_channels = _safe_scalar(
            conn,
            """
            SELECT COUNT(DISTINCT channel_name) FROM public.slack_messages
            WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days'
            """,
            (user_id,),
        )

        # ── Health ─────────────────────────────────────────────────────────
        health_today = _safe_query(
            conn,
            """
            SELECT source, steps, active_minutes, calories, distance_km, sleep_hours,
                   heart_rate_bpm, heart_points
            FROM public.health_snapshots
            WHERE user_id = %s AND snapshot_date = %s
            """,
            (user_id, today),
        )
        health_summary = {}
        for h in health_today:
            if h.get("steps"):
                health_summary["steps"] = (health_summary.get("steps") or 0) + h["steps"]
            if h.get("active_minutes"):
                health_summary["active_minutes"] = (health_summary.get("active_minutes") or 0) + h["active_minutes"]
            if h.get("calories"):
                health_summary["calories"] = (health_summary.get("calories") or 0) + h["calories"]
            if h.get("sleep_hours"):
                health_summary["sleep_hours"] = max(health_summary.get("sleep_hours") or 0, h["sleep_hours"])
            if h.get("distance_km"):
                health_summary["distance_km"] = max(health_summary.get("distance_km") or 0, h["distance_km"])
            if h.get("heart_rate_bpm"):
                health_summary["heart_rate_bpm"] = max(health_summary.get("heart_rate_bpm") or 0, h["heart_rate_bpm"])
            if h.get("heart_points"):
                health_summary["heart_points"] = (health_summary.get("heart_points") or 0) + h["heart_points"]

        health_weekly_rows = _safe_query(
            conn,
            """
            SELECT snapshot_date, steps, calories, distance_km
            FROM public.health_snapshots
            WHERE user_id = %s
              AND source = 'google_fit'
              AND snapshot_date >= %s
              AND snapshot_date <= %s
            ORDER BY snapshot_date
            """,
            (user_id, today - timedelta(days=6), today),
        )
        health_by_date = {
            _local_date_key(row["snapshot_date"]): row
            for row in health_weekly_rows
            if row.get("snapshot_date")
        }
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        health_weekly = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            key = _local_date_key(day)
            row = health_by_date.get(key, {})
            health_weekly.append(
                {
                    "date": key,
                    "label": day_names[day.weekday()],
                    "steps": row.get("steps") or 0,
                    "calories": row.get("calories") or 0,
                    "distance_km": row.get("distance_km") or 0,
                }
            )

        # ── GitHub ─────────────────────────────────────────────────────────
        github_row = _safe_query(
            conn,
            "SELECT github_username, avatar_url FROM public.github_auth WHERE user_id = %s",
            (user_id,),
        )
        github_connected = len(github_row) > 0
        github_username = github_row[0]["github_username"] if github_row else None

        # ── Journal ────────────────────────────────────────────────────────
        journal_today = _safe_query(
            conn,
            """
            SELECT title, mood, ai_summary FROM public.journal_entries
            WHERE user_id = %s AND entry_date = %s
            """,
            (user_id, today),
        )
        journal_streak = 0
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT entry_date FROM public.journal_entries
                WHERE user_id = %s ORDER BY entry_date DESC LIMIT 30
                """,
                (user_id,),
            )
            dates = [r[0] for r in cur.fetchall()]
            cur.close()
            check = today
            for d in dates:
                if d == check:
                    journal_streak += 1
                    check -= timedelta(days=1)
                else:
                    break
        except Exception:
            pass

        return JSONResponse(
            content={
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "inprogress": inprogress_tasks,
                    "pending": pending_tasks,
                    "today": {
                        "total": today_completed_tasks + today_inprogress_tasks + today_pending_tasks,
                        "completed": today_completed_tasks,
                        "inprogress": today_inprogress_tasks,
                        "pending": today_pending_tasks,
                    },
                    "streak": task_streak,
                    "recent": recent_tasks,
                },
                "calendar": {
                    "today_events": today_events,
                    "upcoming": upcoming_events,
                },
                "slack": {
                    "messages_7d": slack_messages_7d,
                    "active_channels": slack_channels,
                },
                "health": health_summary,
                "health_weekly": health_weekly,
                "github": {
                    "connected": github_connected,
                    "username": github_username,
                },
                "journal": {
                    "has_today": len(journal_today) > 0,
                    "today_mood": journal_today[0]["mood"] if journal_today else None,
                    "streak": journal_streak,
                },
            },
            headers={"Cache-Control": "private, max-age=30"},
        )
    finally:
        conn.close()
