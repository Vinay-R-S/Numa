import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, timedelta, timezone

from ..auth.dependencies import get_current_user
from . import service as task_service
from .repository import task_repository
from .schemas import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── List active tasks (board view) ────────────────────────────────────────────
# Completed tasks that were completed on a previous calendar day are excluded
# from the board; they appear in GET /tasks/history instead.
@router.get("", response_model=List[TaskResponse])
def list_tasks(current_user: dict = Depends(get_current_user)):
    return task_repository.list_active(current_user["sub"])


# ── Completed-task history (tasks completed before today) ──────────────────────
@router.get("/history", response_model=List[TaskResponse])
def list_task_history(current_user: dict = Depends(get_current_user)):
    return task_repository.list_history(current_user["sub"])


# ── Create task ────────────────────────────────────────────────────────────────
@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, current_user: dict = Depends(get_current_user)):
    row = task_repository.insert(
        user_id=current_user["sub"],
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
        reminder_at=body.reminder_at,
        source_name=body.source_name,
        source_logo=body.source_logo,
        position=body.position,
    )
    task_service.store_task_snapshot(row)
    return row


# ── Update task (full) ─────────────────────────────────────────────────────────
@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]

    # Build partial update from non-None fields
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update.")

    # Handle completed_at when status changes to/from 'completed'
    if "status" in fields:
        if fields["status"] == "completed":
            fields["completed_at"] = datetime.now(timezone.utc)
        else:
            fields["completed_at"] = None

    # First, fetch the task to check for external_ref (calendar sync)
    existing_task = task_repository.get_sync_fields(task_id, user_id)
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found.")

    external_ref = existing_task[0]

    # Local write first, outward sync after. Google Calendar used to be mutated
    # before the row was touched, so a concurrent delete or a failed update left
    # the user with a 404 or 500 while their calendar event had already been
    # retitled and rescheduled. Writing locally first is also what makes the
    # log-and-continue handler below correct rather than lossy
    # (NUMA-142 P6, PLAN 7).
    task = task_repository.update_partial(task_id, user_id, fields)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task_service.store_task_snapshot(task)

    _sync_task_update_to_calendar(user_id, external_ref, task)
    return task


def _sync_task_update_to_calendar(user_id: str, external_ref, task: dict) -> None:
    """Push a committed task change out to its linked Google Calendar event."""
    if not external_ref or not str(external_ref).startswith("gcal:"):
        return

    # Format: gcal:calendar_id:event_id or gcal:ical:ical_uid
    parts = str(external_ref).split(":", 2)
    if len(parts) < 3 or parts[1] == "ical":
        return

    due_date = task.get("due_date")
    if not due_date:
        return

    try:
        from ..calendar.service import update_event_from_payload
        from ..calendar.schemas import CalendarEventUpsert

        due_dt = (
            due_date
            if isinstance(due_date, datetime)
            else datetime.fromisoformat(str(due_date).replace("Z", "+00:00"))
        )
        end_dt = due_dt + timedelta(hours=1)

        update_event_from_payload(
            f"{parts[1]}:{parts[2]}",
            CalendarEventUpsert(
                title=task.get("title") or "",
                date=due_dt.strftime("%Y-%m-%d"),
                startTime=due_dt.strftime("%H:%M"),
                endTime=end_dt.strftime("%H:%M"),
                description=task.get("description") or "",
            ),
            user_id=user_id,
        )
    except Exception as exc:
        # Logged, not fatal: the task change is already committed.
        log.warning("Failed to sync the task update to Google Calendar: %s", exc)


# ── Patch status (used by DnD) ─────────────────────────────────────────────────
@router.patch("/{task_id}/status", response_model=TaskResponse)
def patch_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    completed_at = (
        datetime.now(timezone.utc) if body.status == "completed" else None
    )
    task = task_repository.update_status(
        task_id, user_id, body.status, completed_at, body.position
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task_service.store_task_snapshot(task)
    return task


# ── Delete task ────────────────────────────────────────────────────────────────
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    existing = task_repository.get_external_ref(task_id, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found.")

    external_ref = existing[0]
    is_calendar_task = bool(external_ref and str(external_ref).startswith("gcal:"))

    # The row first, the Google event after: the same inversion as update_task
    # (NUMA-142 P6, PLAN 7).
    deleted = task_repository.delete(task_id, user_id)
    if deleted == 0 and not is_calendar_task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task_service.delete_task_snapshot(user_id, task_id)

    if is_calendar_task:
        try:
            from ..calendar.service import delete_event_by_id

            parts = str(external_ref).split(":", 2)
            if len(parts) >= 3 and parts[1] != "ical":
                delete_event_by_id(f"{parts[1]}:{parts[2]}", user_id=user_id)
        except Exception as exc:
            log.warning("Failed to sync the task delete to Google Calendar: %s", exc)


# ── Stats for analytics ────────────────────────────────────────────────────────
@router.get("/stats")
def get_task_stats(current_user: dict = Depends(get_current_user)):
    return task_repository.stats(current_user["sub"])
