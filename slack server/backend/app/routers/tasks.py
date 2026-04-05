"""Tasks CRUD."""
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, TaskCreate, TaskUpdate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _bump_analytics(db, user_id: str, field: str, delta: int = 1):
    """Increment or decrement an analytics counter for today."""
    today = date.today().isoformat()
    resp = db.table("analytics").select("id," + field).eq("user_id", user_id).eq("period_date", today).limit(1).execute()
    if resp.data:
        row = resp.data[0]
        new_val = max(0, (row.get(field) or 0) + delta)
        db.table("analytics").update({field: new_val}).eq("id", row["id"]).execute()
    elif delta > 0:
        db.table("analytics").insert({"user_id": user_id, "period_date": today, field: delta}).execute()


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = None,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    q = db.table("tasks").select("*").eq("user_id", current_user.id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).execute()
    return [TaskOut(**t) for t in (resp.data or [])]


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    payload: TaskCreate,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    row = {
        "user_id": current_user.id,
        **payload.model_dump(exclude_none=True),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
    }
    resp = db.table("tasks").insert(row).execute()
    _bump_analytics(db, current_user.id, "tasks_created", 1)
    return TaskOut(**resp.data[0])


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    # Ownership check — also fetch current status to detect transitions
    check = db.table("tasks").select("id,status").eq("id", task_id).eq("user_id", current_user.id).single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_none=True)
    if "due_date" in updates and updates["due_date"]:
        updates["due_date"] = updates["due_date"].isoformat()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    resp = db.table("tasks").update(updates).eq("id", task_id).execute()

    # Bump analytics on status transitions
    new_status = updates.get("status")
    old_status = check.data.get("status")
    if new_status and new_status != old_status:
        if new_status == "done":
            _bump_analytics(db, current_user.id, "tasks_completed", 1)
        elif old_status == "done":
            # Un-ticking a completed task — decrement
            _bump_analytics(db, current_user.id, "tasks_completed", -1)

    return TaskOut(**resp.data[0])


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    check = db.table("tasks").select("id").eq("id", task_id).eq("user_id", current_user.id).single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found")
    db.table("tasks").delete().eq("id", task_id).execute()
