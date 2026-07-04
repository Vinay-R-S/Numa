import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..memory import memory_service
from .repository import task_repository


GCAL_SOURCE_NAME = "Google Calendar"
GCAL_SOURCE_LOGO = "google-calendar"


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
        due = task.get("due_date")
        due_text = due.isoformat() if hasattr(due, "isoformat") else (str(due) if due else "none")
        text = (
            f"Task: {str(task.get('title') or 'Untitled')}\n"
            f"Status: {str(task.get('status') or 'planned')}\n"
            f"Priority: {str(task.get('priority') or 'medium')}\n"
            f"Due: {due_text}\n"
            f"Source: {str(task.get('source_name') or 'manual')}\n"
            f"Details: {str(task.get('description') or 'none')}"
        )
        memory_service.upsert_domain_text(
            user_id=user_id,
            domain="tasks",
            stable_key=task_id,
            text=text,
            payload={
                "task_id": task_id,
                "title": task.get("title"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "due_date": due_text if due_text != "none" else None,
                "external_ref": task.get("external_ref"),
            },
        )
    except Exception:
        # Memory ingest is best-effort and must not break task writes.
        return


def store_task_snapshot(task: Dict) -> None:
    _store_task_snapshot(task)


def delete_task_snapshot(user_id: str, task_id: str) -> None:
    try:
        if user_id and task_id:
            memory_service.delete_snapshot(
                user_id=user_id,
                source="task",
                external_id=str(task_id),
            )
            memory_service.delete_domain_point(
                user_id=user_id,
                domain="tasks",
                stable_key=str(task_id),
            )
    except Exception:
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
    task = task_repository.upsert_calendar_event_task(
        user_id=user_id,
        external_ref=external_ref,
        title=title,
        description=description,
        due_date=due_date,
        reminder_at=reminder_at,
        source_name=GCAL_SOURCE_NAME,
        source_logo=GCAL_SOURCE_LOGO,
    )
    _store_task_snapshot(task)


def delete_task_by_external_ref(user_id: str, external_ref: str) -> int:
    row = task_repository.find_id_by_external_ref(user_id, external_ref)
    deleted = task_repository.delete_by_external_ref(user_id, external_ref)

    if deleted and row and row[0]:
        delete_task_snapshot(user_id, str(row[0]))

    return deleted


def create_task_for_user(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "planned",
    due_date: Optional[datetime] = None,
    source_name: Optional[str] = None,
    source_logo: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> Dict:
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Task title is required")

    dedupe_ref = external_ref
    if not dedupe_ref:
        due_key = due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date or "")
        raw_key = "|".join(
            [
                normalized_title.lower(),
                (description or "").strip().lower(),
                status.strip().lower(),
                due_key,
                (source_name or "agent").strip().lower(),
            ]
        )
        dedupe_ref = f"agent:{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:24]}"

    task = task_repository.upsert_agent_task(
        user_id=user_id,
        title=normalized_title,
        description=description,
        status=status,
        due_date=due_date,
        source_name=source_name,
        source_logo=source_logo,
        external_ref=dedupe_ref,
    )
    _store_task_snapshot(task)
    return task


def update_task_by_title(
    user_id: str,
    title: str,
    new_title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Dict]:
    row = task_repository.find_id_by_title(user_id, title)
    if not row:
        return None

    task_id = row[0]
    updates: Dict = {}
    if new_title is not None:
        updates["title"] = new_title
    if description is not None:
        updates["description"] = description
    if status is not None:
        updates["status"] = status
        updates["completed_at"] = datetime.now(timezone.utc) if status == "completed" else None

    if not updates:
        existing = task_repository.get_by_id(task_id, user_id)
        _store_task_snapshot(existing)
        return existing

    updated = task_repository.update_by_id(task_id, user_id, updates)
    _store_task_snapshot(updated)
    return updated


def delete_task_by_title(user_id: str, title: str) -> int:
    row = task_repository.find_id_by_title(user_id, title)
    deleted = task_repository.delete_latest_by_title(user_id, title)

    if deleted and row and row[0]:
        memory_service.delete_snapshot(
            user_id=user_id,
            source="task",
            external_id=str(row[0]),
        )

    return deleted


def list_recent_tasks(user_id: str, limit: int = 10) -> List[Dict]:
    return task_repository.list_recent(user_id, limit)
