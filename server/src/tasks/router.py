from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, timezone

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from .schemas import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _row_to_dict(row, cursor_description) -> dict:
    return {col.name: val for col, val in zip(cursor_description, row)}


# ── List active tasks (board view) ────────────────────────────────────────────
# Completed tasks that were completed on a previous calendar day are excluded
# from the board; they appear in GET /tasks/history instead.
@router.get("", response_model=List[TaskResponse])
def list_tasks(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, title, description, status, priority,
                   due_date, reminder_at, source_name, source_logo,
                   external_ref, position, completed_at, created_at, updated_at
            FROM public.tasks
            WHERE user_id = %s
              AND (
                  status != 'completed'
                  OR completed_at >= DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')
              )
            ORDER BY status, position ASC, created_at ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        tasks = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return tasks
    finally:
        conn.close()


# ── Completed-task history (tasks completed before today) ──────────────────────
@router.get("/history", response_model=List[TaskResponse])
def list_task_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, title, description, status, priority,
                   due_date, reminder_at, source_name, source_logo,
                   external_ref, position, completed_at, created_at, updated_at
            FROM public.tasks
            WHERE user_id = %s
              AND status = 'completed'
              AND (
                  completed_at IS NULL
                  OR completed_at < DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')
              )
            ORDER BY completed_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        tasks = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return tasks
    finally:
        conn.close()


# ── Create task ────────────────────────────────────────────────────────────────
@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.tasks
                (user_id, title, description, status, priority,
                 due_date, reminder_at, source_name, source_logo, position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, title, description, status, priority,
                      due_date, reminder_at, source_name, source_logo,
                      external_ref, position, completed_at, created_at, updated_at
            """,
            (
                user_id,
                body.title,
                body.description,
                body.status,
                body.priority,
                body.due_date,
                body.reminder_at,
                body.source_name,
                body.source_logo,
                body.position,
            ),
        )
        row = _row_to_dict(cur.fetchone(), cur.description)
        conn.commit()
        cur.close()
        return row
    finally:
        conn.close()


# ── Update task (full) ─────────────────────────────────────────────────────────
@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()

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
        cur.execute(
            """
            SELECT external_ref, title, description, due_date
            FROM public.tasks
            WHERE id = %s AND user_id = %s
            """,
            (task_id, user_id),
        )
        existing_task = cur.fetchone()
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found.")

        external_ref = existing_task[0]

        # If this task is linked to a calendar event, sync the changes back
        if external_ref and external_ref.startswith("gcal:"):
            try:
                from ..calendar.service import update_event_from_payload
                from ..calendar.schemas import CalendarEventUpsert

                # Parse external_ref to get calendar_id and event_id
                # Format: gcal:calendar_id:event_id or gcal:ical:ical_uid
                parts = external_ref.split(":", 2)
                if len(parts) >= 3 and parts[1] != "ical":
                    calendar_id = parts[1]
                    event_id = parts[2]
                    composite_event_id = f"{calendar_id}:{event_id}"

                    # Build calendar event payload from task fields
                    title = fields.get("title", existing_task[1])
                    description = fields.get("description", existing_task[2] or "")
                    due_date = fields.get("due_date", existing_task[3])

                    if due_date:
                        from datetime import datetime as dt
                        if isinstance(due_date, dt):
                            date_str = due_date.strftime("%Y-%m-%d")
                            time_str = due_date.strftime("%H:%M")
                        else:
                            # Parse string datetime
                            due_dt = dt.fromisoformat(str(due_date).replace('Z', '+00:00'))
                            date_str = due_dt.strftime("%Y-%m-%d")
                            time_str = due_dt.strftime("%H:%M")

                        # Update the calendar event
                        calendar_payload = CalendarEventUpsert(
                            title=title,
                            date=date_str,
                            startTime=time_str,
                            endTime=time_str,
                            description=description or "",
                        )
                        update_event_from_payload(composite_event_id, calendar_payload, user_id=user_id)
            except Exception as e:
                # Log but don't fail the task update if calendar sync fails
                import logging
                logging.warning(f"Failed to sync task update to calendar: {e}")

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values())
        values.extend([task_id, user_id])

        cur.execute(
            f"""
            UPDATE public.tasks
            SET {set_clause}
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, title, description, status, priority,
                      due_date, reminder_at, source_name, source_logo,
                      external_ref, position, completed_at, created_at, updated_at
            """,
            values,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found.")
        task = _row_to_dict(row, cur.description)
        conn.commit()
        cur.close()
        return task
    finally:
        conn.close()


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
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE public.tasks
            SET status = %s,
                completed_at = %s,
                position = COALESCE(%s, position)
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, title, description, status, priority,
                      due_date, reminder_at, source_name, source_logo,
                      external_ref, position, completed_at, created_at, updated_at
            """,
            (body.status, completed_at, body.position, task_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found.")
        task = _row_to_dict(row, cur.description)
        conn.commit()
        cur.close()
        return task
    finally:
        conn.close()


# ── Delete task ────────────────────────────────────────────────────────────────
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM public.tasks WHERE id = %s AND user_id = %s",
            (task_id, user_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found.")
        conn.commit()
        cur.close()
    finally:
        conn.close()


# ── Stats for analytics ────────────────────────────────────────────────────────
@router.get("/stats")
def get_task_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Tasks by status
        cur.execute(
            "SELECT status, COUNT(*) FROM public.tasks WHERE user_id = %s GROUP BY status",
            (user_id,),
        )
        by_status = [{"status": r[0], "count": r[1]} for r in cur.fetchall()]

        # Completed per day (last 30 days)
        cur.execute(
            """
            SELECT DATE(completed_at AT TIME ZONE 'UTC') as day, COUNT(*)
            FROM public.tasks
            WHERE user_id = %s
              AND completed_at IS NOT NULL
              AND completed_at >= NOW() - INTERVAL '30 days'
            GROUP BY day ORDER BY day
            """,
            (user_id,),
        )
        daily = [{"date": str(r[0]), "count": r[1]} for r in cur.fetchall()]

        # Completed per week (last 12 weeks)
        cur.execute(
            """
            SELECT DATE_TRUNC('week', completed_at AT TIME ZONE 'UTC') as week, COUNT(*)
            FROM public.tasks
            WHERE user_id = %s
              AND completed_at IS NOT NULL
              AND completed_at >= NOW() - INTERVAL '12 weeks'
            GROUP BY week ORDER BY week
            """,
            (user_id,),
        )
        weekly = [{"date": str(r[0])[:10], "count": r[1]} for r in cur.fetchall()]

        # Completed per month (last 12 months)
        cur.execute(
            """
            SELECT DATE_TRUNC('month', completed_at AT TIME ZONE 'UTC') as month, COUNT(*)
            FROM public.tasks
            WHERE user_id = %s
              AND completed_at IS NOT NULL
              AND completed_at >= NOW() - INTERVAL '12 months'
            GROUP BY month ORDER BY month
            """,
            (user_id,),
        )
        monthly = [{"date": str(r[0])[:7], "count": r[1]} for r in cur.fetchall()]

        # Completed per year (all time)
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM completed_at AT TIME ZONE 'UTC')::int as year, COUNT(*)
            FROM public.tasks
            WHERE user_id = %s AND completed_at IS NOT NULL
            GROUP BY year ORDER BY year
            """,
            (user_id,),
        )
        yearly = [{"date": str(r[0]), "count": r[1]} for r in cur.fetchall()]

        # Total count
        cur.execute(
            "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s", (user_id,)
        )
        total = cur.fetchone()[0]

        # Current streak (consecutive days with at least 1 completed task, ending today)
        cur.execute(
            """
            WITH daily_completions AS (
                SELECT DISTINCT DATE(completed_at AT TIME ZONE 'UTC') as day
                FROM public.tasks
                WHERE user_id = %s AND completed_at IS NOT NULL
            ),
            numbered AS (
                SELECT day,
                       day - (ROW_NUMBER() OVER (ORDER BY day))::int * INTERVAL '1 day' AS grp
                FROM daily_completions
            )
            SELECT COUNT(*) FROM numbered
            WHERE grp = (
                SELECT day - (ROW_NUMBER() OVER (ORDER BY day))::int * INTERVAL '1 day'
                FROM numbered
                WHERE day = CURRENT_DATE
                LIMIT 1
            )
            """,
            (user_id,),
        )
        streak_row = cur.fetchone()
        streak = streak_row[0] if streak_row else 0

        cur.close()
        return {
            "total": total,
            "by_status": by_status,
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "yearly": yearly,
            "streak": streak,
        }
    finally:
        conn.close()
