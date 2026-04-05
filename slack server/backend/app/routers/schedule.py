"""Schedule / plans endpoints."""
from datetime import date
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, PlanCreate, PlanOut

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/today", response_model=PlanOut | None)
async def get_today_schedule(current_user: UserOut = Depends(get_current_user)):
    db = get_supabase()
    today = date.today().isoformat()
    resp = (
        db.table("plans")
        .select("*")
        .eq("user_id", current_user.id)
        .eq("plan_date", today)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return PlanOut(**resp.data[0])


@router.post("/plan", response_model=PlanOut, status_code=201)
async def save_plan(
    payload: PlanCreate,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    row = {
        "user_id": current_user.id,
        "plan_date": payload.plan_date.isoformat(),
        "blocks": [b.model_dump() for b in payload.blocks],
        "summary": payload.summary,
    }
    # Upsert so re-planning today overwrites the old plan
    resp = (
        db.table("plans")
        .upsert(row, on_conflict="user_id,plan_date")
        .execute()
    )
    return PlanOut(**resp.data[0])
