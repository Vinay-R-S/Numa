"""Calendar -> task/memory sync helpers (NUMA-104 P3, PLAN 16.1).

Extracted verbatim from calendar/service.py; service.py re-exports these names.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..memory import memory_service
from ..tasks import service as task_service
from .datetime_utils import TIMEZONE, _to_local, _iso_to_datetime, _event_datetime_bounds
from .google_client import _run_parallel_best_effort

log = logging.getLogger(__name__)


def _upsert_calendar_event_memory(user_id: Optional[str], event: Dict) -> None:
    if not user_id:
        return

    event_id    = str(event.get("id")             or "").strip()
    calendar_id = str(event.get("_calendar_id")   or "primary")
    if not event_id:
        return

    start_at, end_at, _, _, _ = _event_datetime_bounds(event)
    memory_service.store_calendar_event_snapshot(
        user_id=user_id,
        calendar_id=calendar_id,
        event_id=event_id,
        summary=str(event.get("summary") or "(No title)"),
        start_at=start_at,
        end_at=end_at,
        status=str(event.get("status") or "confirmed"),
        description=event.get("description"),
    )


def _calendar_event_due_date(event: Dict) -> Optional[datetime]:
    start_data = event.get("start", {})
    dt_raw     = start_data.get("dateTime")
    if dt_raw:
        return _iso_to_datetime(dt_raw)

    date_raw = start_data.get("date")
    if date_raw:
        return datetime.fromisoformat(f"{date_raw}T09:00:00").replace(tzinfo=TIMEZONE)

    return None


def _sync_calendar_event_to_task(user_id: Optional[str], event: Dict) -> None:
    """
    Sync a personal calendar event to the tasks table - TODAY's timed events only.

    Rules:
    - Holiday and birthday calendars are always skipped.
    - All-day observances (is_all_day=True for holiday/birthday) are skipped.
    - Only events whose *start date* falls on today (local timezone) are synced.
      Future or past events are NOT added to the task list.
    """
    if not user_id:
        return

    # Skip non-personal events (holidays/birthdays are not tasks)
    cal_type = str(event.get("_calendar_type") or "personal")
    if cal_type in ("holiday", "birthday"):
        return

    # Determine if this event starts today
    start_data = event.get("start", {})
    start_dt_raw = start_data.get("dateTime")
    start_date_raw = start_data.get("date")

    today_local = datetime.now(TIMEZONE).date()

    if start_dt_raw:
        # Timed event - must start today
        event_start = _to_local(_iso_to_datetime(start_dt_raw))
        if event_start.date() != today_local:
            return  # Not today - skip
        is_all_day_event = False
    elif start_date_raw:
        # All-day event - only sync if it's today AND from a personal (non-holiday) calendar
        try:
            event_date = datetime.fromisoformat(start_date_raw).date()
        except ValueError:
            return
        if event_date != today_local:
            return  # Not today - skip
        is_all_day_event = True
    else:
        return  # No usable date - skip

    event_id    = str(event.get("id")              or "").strip()
    calendar_id = str(event.get("_calendar_id")    or "primary")

    if not event_id:
        return

    external_ref = task_service.calendar_external_ref(calendar_id, event_id)

    if str(event.get("status") or "").lower() == "cancelled":
        _run_parallel_best_effort(
            lambda: task_service.delete_task_by_external_ref(user_id, external_ref),
            lambda: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{calendar_id}:{event_id}",
            ),
        )
        return

    summary      = str(event.get("summary")     or "(No title)").strip() or "(No title)"
    description  = str(event.get("description") or "").strip()
    calendar_name = str(event.get("_calendar_summary") or "").strip()
    if calendar_name and not description:
        description = f"From {calendar_name}"

    due_date = _calendar_event_due_date(event)

    # Set reminder 15 minutes before the event for timed events
    reminder_at: Optional[datetime] = None
    if not is_all_day_event and start_dt_raw:
        try:
            reminder_at = _to_local(_iso_to_datetime(start_dt_raw)) - timedelta(minutes=15)
        except Exception:
            log.debug("Could not derive a reminder time from %r", start_dt_raw, exc_info=True)

    _run_parallel_best_effort(
        lambda: task_service.upsert_calendar_event_task(
            user_id=user_id,
            external_ref=external_ref,
            title=summary,
            description=description or None,
            due_date=due_date,
            reminder_at=reminder_at,
        ),
        lambda: _upsert_calendar_event_memory(user_id, event),
    )


def _sync_all_events_to_tasks(user_id: Optional[str], events: List[Dict]) -> None:
    if not user_id:
        return
    for event in events:
        _sync_calendar_event_to_task(user_id, event)
