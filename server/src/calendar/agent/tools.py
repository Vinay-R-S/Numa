"""Agent-facing calendar tools: create/modify/delete/find by description
(NUMA-104 P3, PLAN 16.1).

Thin orchestration over the calendar helper modules. Extracted verbatim from
calendar/service.py; service.py re-exports these names.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..datetime_utils import (
    TIMEZONE,
    TIMEZONE_NAME,
    parse_datetime,
    force_local,
    _iso_to_datetime,
)
from ..google_auth import get_calendar_service
from ..google_client import (
    fetch_events_across_selected_calendars,
    _parse_calendar_event_id,
)
from ..calendars import list_selected_calendars
from ..repository import _persist_mutated_event, _delete_cal_event_cleanup
from ..sync import _sync_calendar_event_to_task


def is_duplicate_event(service, title: str, start_iso: str) -> bool:
    start_dt = _iso_to_datetime(start_iso)
    time_min = (start_dt - timedelta(hours=2)).isoformat()
    time_max = (start_dt + timedelta(hours=2)).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    title_lower = title.strip().lower()
    for event in events_result.get("items", []):
        if event.get("summary", "").strip().lower() == title_lower:
            return True

    return False


def create_calendar_event(
    title: str,
    datetime_str: str,
    duration_minutes: int = 60,
    attendees: Optional[List[str]] = None,
    create_meet: bool = False,
    user_id: Optional[str] = None,
) -> Dict:
    service  = get_calendar_service(user_id=user_id)
    parsed_dt = parse_datetime(datetime_str)
    start_dt  = force_local(parsed_dt)
    end_dt    = start_dt + timedelta(minutes=duration_minutes)
    start_iso = start_dt.isoformat()

    if is_duplicate_event(service, title, start_iso):
        return {"status": "duplicate_prevented", "summary": title, "start": start_iso}

    event: Dict[str, Any] = {
        "summary": title,
        "start": {"dateTime": start_iso,            "timeZone": TIMEZONE_NAME},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": TIMEZONE_NAME},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 30},
            ],
        },
    }

    if create_meet:
        event["conferenceData"] = {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    if attendees:
        event["attendees"] = [{"email": em.strip()} for em in attendees if em and em.strip()]

    created_event = (
        service.events()
        .insert(calendarId="primary", body=event, conferenceDataVersion=1 if create_meet else 0)
        .execute()
    )

    created_event["_calendar_id"]   = "primary"
    created_event["_calendar_type"] = "personal"
    created_event.setdefault("_calendar_summary", "Primary")
    created_event.setdefault("status", "confirmed")
    _persist_mutated_event(user_id, service, created_event)
    _sync_calendar_event_to_task(user_id, created_event)

    meet_link = None
    for entry in (created_event.get("conferenceData") or {}).get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            meet_link = entry.get("uri")
            break

    return {
        "event_id":  created_event.get("id"),
        "link":      created_event.get("htmlLink"),
        "meet_link": meet_link,
        "summary":   created_event.get("summary"),
        "start":     created_event["start"].get("dateTime"),
        "attendees": [a.get("email") for a in created_event.get("attendees", [])],
    }


def delete_calendar_event(event_id: str, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)
    try:
        service.events().delete(calendarId=calendar_id, eventId=actual_event_id).execute()
    except Exception as exc:
        err_str = str(exc)
        if "410" not in err_str and "Resource has been deleted" not in err_str:
            raise
    _delete_cal_event_cleanup(user_id, calendar_id, actual_event_id)
    return {"status": "success", "deleted_event_id": actual_event_id}


def find_events_by_description(query: str, user_id: Optional[str] = None) -> List[Dict]:
    service = get_calendar_service(user_id=user_id)

    now          = datetime.now(TIMEZONE)
    today_midnight = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=TIMEZONE)
    time_min     = today_midnight.isoformat()
    time_max     = (now + timedelta(days=7)).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    query_lower = query.strip().lower()
    matches: List[Dict] = []
    for event in events_result.get("items", []):
        summary = event.get("summary", "")
        if query_lower in summary.lower():
            matches.append(
                {
                    "summary": summary,
                    "start":   event["start"].get("dateTime", event["start"].get("date")),
                    "id":      event.get("id"),
                }
            )

    return matches


def delete_event_by_description(query: str, user_id: Optional[str] = None) -> Dict:
    matches = find_events_by_description(query, user_id=user_id)

    if not matches:
        return {"status": "not_found", "message": f"No matching event found for '{query}' in the next 7 days."}

    if len(matches) == 1:
        event   = matches[0]
        service = get_calendar_service(user_id=user_id)
        try:
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
        except Exception as exc:
            err_str = str(exc)
            if "410" not in err_str and "Resource has been deleted" not in err_str:
                raise
        _delete_cal_event_cleanup(user_id, "primary", event["id"])
        return {
            "status":         "deleted",
            "deleted_summary": event["summary"],
            "deleted_start":   event["start"],
            "deleted_id":      event["id"],
        }

    return {
        "status":  "multiple_matches",
        "message": f"Found {len(matches)} events matching '{query}'. Please specify which one:",
        "matches": [{"summary": m["summary"], "start": m["start"], "id": m["id"]} for m in matches],
    }


def modify_event_by_description(query: str, new_datetime_str: str, user_id: Optional[str] = None) -> Dict:
    matches = find_events_by_description(query, user_id=user_id)

    if not matches:
        return {"status": "not_found", "message": f"No matching event found for '{query}' in the next 7 days."}

    if len(matches) > 1:
        return {
            "status":  "multiple_matches",
            "message": f"Found {len(matches)} events matching '{query}'. Please specify which one:",
            "matches": [{"summary": m["summary"], "start": m["start"], "id": m["id"]} for m in matches],
        }

    event_match = matches[0]
    service     = get_calendar_service(user_id=user_id)
    full_event  = service.events().get(calendarId="primary", eventId=event_match["id"]).execute()

    old_start_str = full_event["start"].get("dateTime")
    old_end_str   = full_event["end"].get("dateTime")

    if old_start_str and old_end_str:
        original_duration = _iso_to_datetime(old_end_str) - _iso_to_datetime(old_start_str)
    else:
        original_duration = timedelta(minutes=60)

    new_start = force_local(parse_datetime(new_datetime_str))
    new_end   = new_start + original_duration

    patch_body = {
        "start": {"dateTime": new_start.isoformat(), "timeZone": TIMEZONE_NAME},
        "end":   {"dateTime": new_end.isoformat(),   "timeZone": TIMEZONE_NAME},
    }

    updated_event = (
        service.events()
        .patch(calendarId="primary", eventId=event_match["id"], body=patch_body)
        .execute()
    )

    updated_event["_calendar_id"]   = "primary"
    updated_event["_calendar_type"] = "personal"
    updated_event.setdefault("_calendar_summary", "Primary")
    updated_event.setdefault("status", "confirmed")
    _persist_mutated_event(user_id, service, updated_event)
    _sync_calendar_event_to_task(user_id, updated_event)

    return {
        "status":           "modified",
        "summary":          updated_event.get("summary"),
        "old_start":        old_start_str,
        "new_start":        updated_event["start"].get("dateTime"),
        "new_end":          updated_event["end"].get("dateTime"),
        "duration_minutes": int(original_duration.total_seconds() / 60),
        "link":             updated_event.get("htmlLink"),
    }


def find_free_slots(date_str: str, duration_minutes: int = 30, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)

    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    day_start   = datetime.combine(target_date, datetime.strptime("08:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)
    day_end     = datetime.combine(target_date, datetime.strptime("22:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)

    events = fetch_events_across_selected_calendars(
        service, day_start.isoformat(), day_end.isoformat(),
        selected_calendars=list_selected_calendars(service),
    )

    busy = []
    for event in events:
        start_str = event["start"].get("dateTime")
        end_str   = event["end"].get("dateTime")
        if start_str and end_str:
            busy.append((_iso_to_datetime(start_str), _iso_to_datetime(end_str)))

    busy.sort(key=lambda x: x[0])

    free_slots = []
    cursor = day_start

    for busy_start, busy_end in busy:
        busy_start = max(busy_start, day_start)
        busy_end   = min(busy_end,   day_end)

        if cursor < busy_start:
            gap_minutes = int((busy_start - cursor).total_seconds() / 60)
            if gap_minutes >= duration_minutes:
                free_slots.append(
                    {
                        "start":            cursor.strftime("%H:%M"),
                        "end":              busy_start.strftime("%H:%M"),
                        "duration_minutes": gap_minutes,
                    }
                )

        cursor = max(cursor, busy_end)

    if cursor < day_end:
        gap_minutes = int((day_end - cursor).total_seconds() / 60)
        if gap_minutes >= duration_minutes:
            free_slots.append(
                {
                    "start":            cursor.strftime("%H:%M"),
                    "end":              day_end.strftime("%H:%M"),
                    "duration_minutes": gap_minutes,
                }
            )

    return {
        "date":               date_str,
        "requested_duration": duration_minutes,
        "free_slots":         free_slots,
        "total_free_slots":   len(free_slots),
    }
