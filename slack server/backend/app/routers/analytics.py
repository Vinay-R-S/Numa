"""Analytics endpoints."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, AnalyticsOut, AnalyticsPeriodOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _calc_score(row: AnalyticsOut) -> int:
    """Derive a 0-100 productivity score from available counters.
    Called when productivity_score is NULL in the DB."""
    task_pts  = min(row.tasks_completed * 20, 60)        # up to 60 pts (3+ tasks)
    cmd_pts   = min(row.commands_used   *  5, 20)        # up to 20 pts (4+ commands)
    focus_pts = min((row.focus_minutes or 0) // 5, 20)  # up to 20 pts (100+ focus mins)
    return min(100, task_pts + cmd_pts + focus_pts)


def _fetch_range(user_id: str, start: date, end: date) -> list[AnalyticsOut]:
    db = get_supabase()
    resp = (
        db.table("analytics")
        .select("*")
        .eq("user_id", user_id)
        .gte("period_date", start.isoformat())
        .lte("period_date", end.isoformat())
        .order("period_date", desc=False)
        .execute()
    )
    rows = resp.data or []

    # Fill in missing days with zero rows so charts are contiguous
    existing = {r["period_date"]: r for r in rows}
    result = []
    current = start
    while current <= end:
        key = current.isoformat()
        row = AnalyticsOut(**existing[key]) if key in existing else AnalyticsOut(period_date=current)
        if row.productivity_score is None:
            row.productivity_score = _calc_score(row)
        result.append(row)
        current += timedelta(days=1)
    return result


@router.get("/week", response_model=AnalyticsPeriodOut)
async def analytics_week(current_user: UserOut = Depends(get_current_user)):
    today = date.today()
    start = today - timedelta(days=6)
    data = _fetch_range(current_user.id, start, today)
    totals = {
        "tasks_completed": sum(d.tasks_completed for d in data),
        "tasks_created": sum(d.tasks_created for d in data),
        "messages_sent": sum(d.messages_sent for d in data),
        "commands_used": sum(d.commands_used for d in data),
        "focus_minutes": sum(d.focus_minutes for d in data),
    }
    return AnalyticsPeriodOut(period="week", data=data, totals=totals)


@router.get("/month", response_model=AnalyticsPeriodOut)
async def analytics_month(current_user: UserOut = Depends(get_current_user)):
    today = date.today()
    start = today - timedelta(days=29)
    data = _fetch_range(current_user.id, start, today)
    totals = {
        "tasks_completed": sum(d.tasks_completed for d in data),
        "tasks_created": sum(d.tasks_created for d in data),
        "messages_sent": sum(d.messages_sent for d in data),
        "commands_used": sum(d.commands_used for d in data),
        "focus_minutes": sum(d.focus_minutes for d in data),
    }
    return AnalyticsPeriodOut(period="month", data=data, totals=totals)


@router.get("/score/today")
async def score_today(current_user: UserOut = Depends(get_current_user)):
    today = date.today().isoformat()
    db = get_supabase()
    resp = (
        db.table("analytics")
        .select("productivity_score,tasks_completed,focus_minutes")
        .eq("user_id", current_user.id)
        .eq("period_date", today)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]
    return {"productivity_score": None, "tasks_completed": 0, "focus_minutes": 0}
