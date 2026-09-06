"""
Shared task tools for all NUMA sub-agents.

Usage in any agent's toolset factory::

    from ..tasks.agent_tools import make_task_tools
    tools = make_task_tools(tool_decorator, user_id, source_name="Health")
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from . import service as task_service


def _parse_due(value: str | None):
    if not value or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def make_task_tools(tool_decorator, user_id: str, source_name: str = "Agent"):
    """
    Build a standard set of task CRUD tools scoped to a user.

    Parameters
    ----------
    tool_decorator : callable
        The LangChain ``@tool`` decorator.
    user_id : str
        Authenticated user UUID.
    source_name : str
        Label for task origin (e.g. "Health", "GitHub", "LeetCode", "Journal").
    """

    @tool_decorator
    def create_task(
        title: str,
        description: str = "",
        status: str = "planned",
        due_datetime: str = "",
        priority: str = "medium",
    ) -> str:
        """Create a new task in the user's NUMA task list.
        title: short imperative description.
        status: planned | inprogress | completed | pending.
        priority: low | medium | high | urgent.
        due_datetime: optional ISO-8601 datetime."""
        try:
            normalized = status.strip().lower() or "planned"
            if normalized not in {"planned", "inprogress", "completed", "pending"}:
                return "Invalid status. Use planned, inprogress, completed, or pending."
            due = _parse_due(due_datetime)
            task = task_service.create_task_for_user(
                user_id=user_id,
                title=title.strip(),
                description=description.strip() or None,
                status=normalized,
                due_date=due,
                source_name=source_name,
                priority=priority.strip().lower() or "medium",
            )
            return f"Task created: {task.get('title')} [{task.get('status')}] (from {source_name})"
        except Exception as exc:
            return f"Error creating task: {exc}"

    @tool_decorator
    def update_task(
        title: str,
        new_title: str = "",
        description: str = "",
        status: str = "",
    ) -> str:
        """Update an existing task found by its current title.
        Provide at least one field to change: new_title, description, or status."""
        try:
            normalized = status.strip().lower() or None
            if normalized and normalized not in {"planned", "inprogress", "completed", "pending"}:
                return "Invalid status. Use planned, inprogress, completed, or pending."
            if not any((new_title.strip(), description.strip(), normalized)):
                return "Provide at least one field to update."
            updated = task_service.update_task_by_title(
                user_id=user_id,
                title=title.strip(),
                new_title=new_title.strip() or None,
                description=description.strip() or None,
                status=normalized,
            )
            if not updated:
                return f"Task not found: {title}"
            return f"Task updated: {updated.get('title')} [{updated.get('status')}]"
        except Exception as exc:
            return f"Error updating task: {exc}"

    @tool_decorator
    def delete_task(title: str) -> str:
        """Delete a task by its title."""
        try:
            deleted = task_service.delete_task_by_title(user_id=user_id, title=title.strip())
            if deleted == 0:
                return f"Task not found: {title}"
            return f"Task deleted: {title}"
        except Exception as exc:
            return f"Error deleting task: {exc}"

    @tool_decorator
    def list_tasks(limit: int = 10) -> str:
        """List recent tasks from the user's NUMA task list."""
        try:
            safe_limit = max(1, min(limit, 50))
            tasks = task_service.list_recent_tasks(user_id=user_id, limit=safe_limit)
            if not tasks:
                return "No tasks found."
            lines = [f"Tasks ({len(tasks)}):"]
            for t in tasks:
                due = t.get("due_date")
                due_text = due.isoformat() if isinstance(due, datetime) else (str(due) if due else "none")
                src = t.get("source_name") or ""
                src_tag = f" [{src}]" if src else ""
                lines.append(f"  - {t.get('title', 'Untitled')} [{t.get('status', 'planned')}] due={due_text}{src_tag}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Error listing tasks: {exc}"

    return [create_task, update_task, delete_task, list_tasks]
