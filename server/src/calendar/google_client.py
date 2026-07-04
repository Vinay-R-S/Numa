"""Google Calendar API fetch/format helpers (NUMA-104 P3, PLAN 16.1).

Depends on the leaf helpers (datetime_utils, calendars) only; no DB or
persistence imports so it stays free of import cycles. Extracted verbatim from
calendar/service.py; service.py re-exports these names.
"""
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .datetime_utils import (
    TIMEZONE,
    TIMEZONE_NAME,
    force_local,
    _to_local,
    _iso_to_datetime,
)
from .calendars import (
    CONTACTS_CALENDAR_MARKER,
    _get_calendar_type,
    _color_for_calendar_type,
    list_all_calendars,
)

log = logging.getLogger(__name__)
SYNC_WORKERS = int(os.getenv("CALENDAR_SYNC_WORKERS", "3"))


def _parse_calendar_event_id(event_id: str) -> Tuple[str, str]:
    if ":" in event_id:
        cal_id, actual_event_id = event_id.split(":", 1)
        return cal_id, actual_event_id
    return "primary", event_id


def _run_parallel_best_effort(*jobs) -> None:
    jobs = [job for job in jobs if callable(job)]
    if not jobs:
        return

    with ThreadPoolExecutor(max_workers=min(SYNC_WORKERS, len(jobs))) as executor:
        futures = [executor.submit(job) for job in jobs]
        for future in futures:
            try:
                future.result()
            except Exception as exc:
                log.warning("Parallel sync job failed: %s", exc)


def _extract_meet_link(event: Dict) -> Optional[str]:
    conference_data = event.get("conferenceData") or {}
    for entry_point in conference_data.get("entryPoints", []):
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri")
    return None


def fetch_events_across_selected_calendars(
    service,
    time_min: str,
    time_max: str,
    selected_calendars: Optional[List[Dict[str, Any]]] = None,
    fetched_calendar_ids: Optional[Set[str]] = None,
) -> List[Dict]:
    """
    Fetch events from (optionally pre-fetched) calendar list.
    Applies type-aware filtering:
    - personal/shared calendars: only return events where user is involved
    - holiday/birthday calendars: return all events (no user-involvement filter)
    """
    combined: List[Dict] = []
    calendars = selected_calendars or list_all_calendars(service)

    for cal in calendars:
        cal_id   = cal.get("id")
        cal_type = cal.get("calendar_type") or _get_calendar_type(cal)
        if not cal_id:
            continue

        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except Exception as exc:
            log.warning("Failed to fetch events for calendar %s: %s", cal_id, exc)
            continue

        if fetched_calendar_ids is not None:
            fetched_calendar_ids.add(str(cal_id))

        for event in result.get("items", []):
            if cal_type in ("personal", "shared", "other"):
                # For user calendars: filter out non-personal events (contacts birthdays etc.)
                if _is_excluded_google_special_event(event, str(cal_id), str(cal.get("summary") or "")):
                    continue
                if not _is_user_related_meeting(event):
                    continue
            # holiday / birthday calendars: include every event as-is

            event["_calendar_id"]          = cal_id
            event["_calendar_summary"]     = cal.get("summary")
            event["_calendar_access_role"] = cal.get("access_role")
            event["_calendar_type"]        = cal_type
            combined.append(event)

    combined.sort(
        key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
    )
    return combined


def _is_excluded_google_special_event(
    event: Dict[str, Any],
    calendar_id: str,
    calendar_summary: str,
) -> bool:
    """Exclude birthday events auto-injected from contacts into personal calendars."""
    event_type = str(event.get("eventType") or "").strip().lower()
    if event_type == "birthday":
        return True

    organizer = event.get("organizer") if isinstance(event.get("organizer"), dict) else {}
    creator   = event.get("creator")   if isinstance(event.get("creator"),   dict) else {}

    source_text = " ".join(
        [str(calendar_id or ""), str(calendar_summary or ""),
         str(organizer.get("email") or ""), str(creator.get("email") or "")]
    ).lower()

    return CONTACTS_CALENDAR_MARKER in source_text


def _is_user_related_meeting(event: Dict[str, Any]) -> bool:
    creator = event.get("creator")
    if isinstance(creator, dict) and bool(creator.get("self")):
        return True

    organizer = event.get("organizer")
    if isinstance(organizer, dict) and bool(organizer.get("self")):
        return True

    attendees = event.get("attendees")
    if isinstance(attendees, list):
        for attendee in attendees:
            if isinstance(attendee, dict) and bool(attendee.get("self")):
                return True

    return False


def _format_event_for_frontend(event: Dict) -> Dict:
    start_data = event.get("start", {})
    end_data   = event.get("end",   {})

    start_dt_raw = start_data.get("dateTime")
    end_dt_raw   = end_data.get("dateTime")

    if start_dt_raw:
        start_dt   = _to_local(_iso_to_datetime(start_dt_raw))
        event_date = start_dt.date().isoformat()
        start_time = start_dt.strftime("%H:%M")
    else:
        event_date = start_data.get("date", datetime.now(TIMEZONE).date().isoformat())
        start_time = "00:00"

    if end_dt_raw:
        end_dt   = _to_local(_iso_to_datetime(end_dt_raw))
        end_time = end_dt.strftime("%H:%M")
    else:
        end_time = "23:59"

    calendar_name = event.get("_calendar_summary")
    cal_type      = event.get("_calendar_type", "personal")
    is_readonly   = event.get("_calendar_access_role") not in (None, "owner", "writer")
    event_id      = event.get("id", "")
    calendar_id   = event.get("_calendar_id") or "primary"
    safe_id       = event_id if not is_readonly else f"{calendar_id}:{event_id}"

    description = event.get("description", "")
    if not description and calendar_name:
        description = f"From {calendar_name}"

    return {
        "id":          safe_id,
        "title":       event.get("summary", "(No title)"),
        "date":        event_date,
        "startTime":   start_time,
        "endTime":     end_time,
        "description": description,
        "color":       _color_for_calendar_type(cal_type),
        "calendarName": calendar_name,
        "readonly":    is_readonly,
    }


def _build_google_event_body(payload) -> Dict:
    start_dt = force_local(datetime.strptime(f"{payload.date} {payload.startTime}", "%Y-%m-%d %H:%M"))
    end_dt   = force_local(datetime.strptime(f"{payload.date} {payload.endTime}",   "%Y-%m-%d %H:%M"))

    if end_dt <= start_dt:
        raise ValueError("endTime must be after startTime")

    return {
        "summary":     payload.title.strip() or "(No title)",
        "description": payload.description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE_NAME},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": TIMEZONE_NAME},
    }
