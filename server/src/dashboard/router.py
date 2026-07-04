"""
Dashboard Router - unified stats aggregation from all NUMA sub-agents.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_user
from .repository import dashboard_repository

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _local_date_key(value: date) -> str:
    return value.isoformat()


def _streak_from_dates(dates: list, today: date) -> int:
    streak = 0
    check = today
    for d in dates:
        if d == check:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


@router.get("/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    now_utc = datetime.now(timezone.utc)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

    raw = dashboard_repository.fetch_stats_raw(user_id, today, today_start, now_utc)

    # ── Tasks ──────────────────────────────────────────────────────────────
    task_streak = _streak_from_dates(raw["task_completed_dates"], today)
    recent_tasks = raw["recent_tasks"]
    for t in recent_tasks:
        for k in ("due_date", "created_at"):
            if isinstance(t.get(k), (datetime, date)):
                t[k] = t[k].isoformat()

    # ── Calendar ───────────────────────────────────────────────────────────
    upcoming_events = raw["upcoming_events"]
    for e in upcoming_events:
        for k in ("start_at", "end_at"):
            if isinstance(e.get(k), datetime):
                e[k] = e[k].isoformat()

    # ── Health ─────────────────────────────────────────────────────────────
    health_summary: dict = {}
    for h in raw["health_today"]:
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

    health_by_date = {
        _local_date_key(row["snapshot_date"]): row
        for row in raw["health_weekly_rows"]
        if row.get("snapshot_date")
    }
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    health_weekly = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        key = _local_date_key(d)
        row = health_by_date.get(key, {})
        health_weekly.append(
            {
                "date": key,
                "label": day_names[d.weekday()],
                "steps": row.get("steps") or 0,
                "calories": row.get("calories") or 0,
                "distance_km": row.get("distance_km") or 0,
            }
        )

    # ── GitHub ─────────────────────────────────────────────────────────────
    github_row = raw["github_row"]
    github_connected = len(github_row) > 0
    github_username = github_row[0]["github_username"] if github_row else None

    # ── Journal ────────────────────────────────────────────────────────────
    journal_today = raw["journal_today"]
    journal_streak = _streak_from_dates(raw["journal_dates"], today)

    return JSONResponse(
        content={
            "tasks": {
                "total": raw["total_tasks"],
                "completed": raw["completed_tasks"],
                "inprogress": raw["inprogress_tasks"],
                "pending": raw["pending_tasks"],
                "today": {
                    "total": raw["today_completed_tasks"] + raw["today_inprogress_tasks"] + raw["today_pending_tasks"],
                    "completed": raw["today_completed_tasks"],
                    "inprogress": raw["today_inprogress_tasks"],
                    "pending": raw["today_pending_tasks"],
                },
                "streak": task_streak,
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
