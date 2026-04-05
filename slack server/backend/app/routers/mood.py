"""Mood logging."""
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, MoodCreate, MoodOut

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("", response_model=MoodOut, status_code=201)
async def log_mood(
    payload: MoodCreate,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    row = {"user_id": current_user.id, **payload.model_dump(exclude_none=True)}
    resp = db.table("mood_logs").insert(row).execute()
    return MoodOut(**resp.data[0])


@router.get("", response_model=list[MoodOut])
async def get_mood_history(
    limit: int = Query(30, le=100),
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    resp = (
        db.table("mood_logs")
        .select("*")
        .eq("user_id", current_user.id)
        .order("logged_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [MoodOut(**m) for m in (resp.data or [])]
