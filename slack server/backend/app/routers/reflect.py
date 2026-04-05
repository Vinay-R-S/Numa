"""Daily reflections."""
from datetime import date
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, ReflectionCreate, ReflectionOut

router = APIRouter(prefix="/reflect", tags=["reflect"])


@router.post("", response_model=ReflectionOut, status_code=201)
async def create_reflection(
    payload: ReflectionCreate,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    reflection_date = (payload.reflection_date or date.today()).isoformat()
    row = {
        "user_id": current_user.id,
        "reflection_date": reflection_date,
        **{k: v for k, v in payload.model_dump(exclude_none=True).items() if k != "reflection_date"},
    }
    resp = db.table("reflections").insert(row).execute()
    return ReflectionOut(**resp.data[0])


@router.get("", response_model=list[ReflectionOut])
async def list_reflections(
    limit: int = Query(10, le=50),
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    resp = (
        db.table("reflections")
        .select("*")
        .eq("user_id", current_user.id)
        .order("reflection_date", desc=True)
        .limit(limit)
        .execute()
    )
    return [ReflectionOut(**r) for r in (resp.data or [])]
