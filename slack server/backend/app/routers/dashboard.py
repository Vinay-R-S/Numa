"""Dashboard endpoint — today's full view."""
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, DashboardToday, TaskOut, MoodOut, MessageOut, PlanOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/today", response_model=DashboardToday)
async def get_today_dashboard(current_user: UserOut = Depends(get_current_user)):
    db = get_supabase()
    today = date.today().isoformat()

    # Tasks due today or created today
    tasks_resp = (
        db.table("tasks")
        .select("*")
        .eq("user_id", current_user.id)
        .or_(f"due_date.eq.{today},and(status.eq.todo,created_at.gte.{today}T00:00:00)")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    tasks = [TaskOut(**t) for t in (tasks_resp.data or [])]
    tasks_completed = sum(1 for t in tasks if t.status == "done")

    # Today's plan
    plan_resp = (
        db.table("plans")
        .select("*")
        .eq("user_id", current_user.id)
        .eq("plan_date", today)
        .limit(1)
        .execute()
    )
    plan = PlanOut(**plan_resp.data[0]) if plan_resp.data else None

    # Latest mood
    mood_resp = (
        db.table("mood_logs")
        .select("*")
        .eq("user_id", current_user.id)
        .order("logged_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_mood = MoodOut(**mood_resp.data[0]) if mood_resp.data else None

    # Unread nudges
    nudge_resp = (
        db.table("nudges")
        .select("id", count="exact")
        .eq("user_id", current_user.id)
        .eq("read", False)
        .execute()
    )
    unread_nudges = nudge_resp.count or 0

    # Recent messages (last 10)
    msg_resp = (
        db.table("messages")
        .select("*")
        .eq("slack_user_id", current_user.slack_user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    recent_messages = [MessageOut(**m) for m in (msg_resp.data or [])]

    # Productivity score from analytics
    analytics_resp = (
        db.table("analytics")
        .select("productivity_score")
        .eq("user_id", current_user.id)
        .eq("period_date", today)
        .limit(1)
        .execute()
    )
    score = analytics_resp.data[0].get("productivity_score") if analytics_resp.data else None

    return DashboardToday(
        user=current_user,
        tasks_today=tasks,
        tasks_completed_today=tasks_completed,
        plan_today=plan,
        latest_mood=latest_mood,
        unread_nudges=unread_nudges,
        productivity_score=score,
        recent_messages=recent_messages,
    )
