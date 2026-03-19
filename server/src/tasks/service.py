from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..db import _get_conn
from ..memory import memory_service


GCAL_SOURCE_NAME = "Google Calendar"
GCAL_SOURCE_LOGO = "google-calendar"


def _row_to_dict(row, cursor_description) -> dict:
    return {col.name: val for col, val in zip(cursor_description, row)}


def _store_task_snapshot(task: Dict) -> None:
    try:
        user_id = str(task.get("user_id") or "").strip()
        task_id = str(task.get("id") or "").strip()
        if not user_id or not task_id:
            return

        memory_service.store_task_snapshot(
            user_id=user_id,
            task_id=task_id,
            title=str(task.get("title") or "Untitled"),
            status=str(task.get("status") or "planned"),
            description=task.get("description"),
            due_date=task.get("due_date"),
            source_name=task.get("source_name"),
            external_ref=task.get("external_ref"),
        )
    except Exception:
        # Memory ingest is best-effort and must not break task writes.
        return


def calendar_external_ref(calendar_id: str, event_id: str) -> str:
    return f"gcal:{calendar_id}:{event_id}"


def upsert_calendar_event_task(
    user_id: str,
    external_ref: str,
    title: str,
    description: Optional[str],
    due_date: Optional[datetime],
    reminder_at: Optional[datetime] = None,
) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.tasks (
                user_id, title, description, status, due_date, reminder_at,
                source_name, source_logo, position, external_ref
            )
            VALUES (%s, %s, %s, 'planned', %s, %s, %s, %s, 0, %s)
            ON CONFLICT (user_id, external_ref)
            DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                due_date = EXCLUDED.due_date,
                reminder_at = EXCLUDED.reminder_at,
                source_name = EXCLUDED.source_name,
                source_logo = EXCLUDED.source_logo,
                updated_at = NOW()
            RETURNING id, user_id, title, description, status, priority,
                      due_date, reminder_at, source_name, source_logo,
                      external_ref, position, completed_at, created_at, updated_at
            """,
            (
                user_id,
                title,
                description,
                due_date,
                reminder_at,
                GCAL_SOURCE_NAME,
                GCAL_SOURCE_LOGO,
                external_ref,
            ),
        )
        task = _row_to_dict(cur.fetchone(), cur.description)
        conn.commit()
        cur.close()
        _store_task_snapshot(task)
    finally:
        conn.close()


def delete_task_by_external_ref(user_id: str, external_ref: str) -> int:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM public.tasks
            WHERE user_id = %s AND external_ref = %s
            LIMIT 1
            """,
            (user_id, external_ref),
        )
        row = cur.fetchone()

        cur.execute(
            "DELETE FROM public.tasks WHERE user_id = %s AND external_ref = %s",
            (user_id, external_ref),
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()

        if deleted and row and row[0]:
            memory_service.delete_snapshot(
                user_id=user_id,
                source="task",
                external_id=str(row[0]),
            )

        return deleted
    finally:
        conn.close()


def create_task_for_user(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "planned",
    due_date: Optional[datetime] = None,
) -> Dict:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.tasks
                (user_id, title, description, status, due_date, position)
            VALUES (%s, %s, %s, %s, %s, 0)
            RETURNING id, user_id, title, description, status, priority,
                      due_date, reminder_at, source_name, source_logo,
                      external_ref, position, completed_at, created_at, updated_at
            """,
            (user_id, title, description, status, due_date),
        )
        task = _row_to_dict(cur.fetchone(), cur.description)
        conn.commit()
        cur.close()
        _store_task_snapshot(task)
        return task
    finally:
        conn.close()


def update_task_by_title(
    user_id: str,
    title: str,
    new_title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM public.tasks
            WHERE user_id = %s AND LOWER(title) = LOWER(%s)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id, title),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return None

        task_id = row[0]
        updates = {}
        if new_title is not None:
            updates["title"] = new_title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
            updates["completed_at"] = datetime.now(timezone.utc) if status == "completed" else None

        if not updates:
            cur.execute(
                """
                SELECT id, user_id, title, description, status, priority,
                       due_date, reminder_at, source_name, source_logo,
                       external_ref, position, completed_at, created_at, updated_at
                FROM public.tasks
                WHERE id = %s AND user_id = %s
                """,
                (task_id, user_id),
            )
            existing = _row_to_dict(cur.fetchone(), cur.description)
            cur.close()
            _store_task_snapshot(existing)
            return existing

        set_clause = ", ".join(f"{key} = %s" for key in updates)
        values = list(updates.values())
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
        updated = _row_to_dict(cur.fetchone(), cur.description)
        conn.commit()
        cur.close()
        _store_task_snapshot(updated)
        return updated
    finally:
        conn.close()


def delete_task_by_title(user_id: str, title: str) -> int:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM public.tasks
            WHERE user_id = %s AND LOWER(title) = LOWER(%s)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id, title),
        )
        row = cur.fetchone()

        cur.execute(
            """
            DELETE FROM public.tasks
            WHERE id IN (
                SELECT id
                FROM public.tasks
                WHERE user_id = %s AND LOWER(title) = LOWER(%s)
                ORDER BY updated_at DESC
                LIMIT 1
            )
            """,
            (user_id, title),
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()

        if deleted and row and row[0]:
            memory_service.delete_snapshot(
                user_id=user_id,
                source="task",
                external_id=str(row[0]),
            )

        return deleted
    finally:
        conn.close()


def list_recent_tasks(user_id: str, limit: int = 10) -> List[Dict]:
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
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        tasks = [_row_to_dict(row, cur.description) for row in rows]
        cur.close()
        return tasks
    finally:
        conn.close()
