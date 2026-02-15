"""
Google Calendar Service
Creates, lists, and deletes calendar events.
Forces Asia/Kolkata (IST) timezone — no UTC conversion, no guessing.
"""

from datetime import datetime, timedelta
from googleapiclient.discovery import build
from services.google_auth import get_credentials
import os
import pytz


# ── IST timezone constant ──────────────────────────────────────
TIMEZONE_NAME = os.getenv('TIMEZONE', 'Asia/Kolkata')
IST = pytz.timezone(TIMEZONE_NAME)


# ── Datetime formats that LLMs commonly produce ───────────────
DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M",
    "%d-%m-%Y %H:%M",
    "%B %d, %Y %I:%M %p",
    "%b %d, %Y %I:%M %p",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
]


def parse_datetime(datetime_str: str) -> datetime:
    """
    Parse a datetime string into a datetime object.
    
    Handles:
      - Standard ISO: 2026-02-13T19:00:00
      - Natural date + time hybrids: todayT22:00:00, tomorrowT19:00, tomorrow 19:00
      - Multiple strptime formats
    
    Returns:
        datetime: Parsed datetime (caller will localize via force_ist)
    """
    cleaned = datetime_str.strip().rstrip('.')
    if cleaned.endswith('Z'):
        cleaned = cleaned[:-1]
    
    # ── Handle natural date prefixes (today, tomorrow, tmr) ────
    NATURAL_PREFIXES = {
        'today': 0,
        'tomorrow': 1,
        'tmr': 1,
    }
    
    lower = cleaned.lower()
    for prefix, day_offset in NATURAL_PREFIXES.items():
        if lower.startswith(prefix):
            # Extract time portion after the prefix
            remainder = cleaned[len(prefix):]
            # Strip separator: T, space, or nothing
            remainder = remainder.lstrip('T').lstrip('t').lstrip()
            
            now = datetime.now(IST)
            base_date = (now + timedelta(days=day_offset)).date()
            
            if remainder:
                # Parse the time portion
                for time_fmt in ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]:
                    try:
                        parsed_time = datetime.strptime(remainder, time_fmt).time()
                        return datetime.combine(base_date, parsed_time)
                    except ValueError:
                        continue
                raise ValueError(
                    f"Could not parse time portion '{remainder}' from '{datetime_str}'."
                )
            else:
                # No time given — midnight
                return datetime.combine(base_date, datetime.min.time())
    
    # ── Try built-in ISO parser ────────────────────────────────
    try:
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        pass
    
    # ── Try each strptime format ───────────────────────────────
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    
    raise ValueError(
        f"Could not parse datetime: '{datetime_str}'. "
        f"Supported: YYYY-MM-DDTHH:MM:SS, today/tomorrowTHH:MM:SS, YYYY-MM-DD HH:MM, etc."
    )


def force_ist(dt: datetime) -> datetime:
    """
    Force a datetime into IST unconditionally.
    - Strips any existing tzinfo
    - Localizes as IST
    - No conversion between timezones — ever.
    """
    naive = dt.replace(tzinfo=None)
    return IST.localize(naive)


def get_calendar_service():
    """Build and return Google Calendar API service."""
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)


def is_duplicate_event(service, title: str, start_iso: str) -> bool:
    """
    Check if an event with the same title exists within ±2 hours of the start time.
    
    Args:
        service: Google Calendar API service
        title: Event title to check
        start_iso: ISO formatted start time
    
    Returns:
        bool: True if a duplicate exists
    """
    start_dt = datetime.fromisoformat(start_iso)
    time_min = (start_dt - timedelta(hours=2)).isoformat()
    time_max = (start_dt + timedelta(hours=2)).isoformat()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    title_lower = title.strip().lower()
    for event in events_result.get('items', []):
        if event.get('summary', '').strip().lower() == title_lower:
            return True
    
    return False


def create_calendar_event(title: str, datetime_str: str, duration_minutes: int = 60, attendees: list = None):
    """
    Create a new calendar event — forced IST, with duplicate prevention,
    Google Meet auto-generation, and optional attendees.
    
    Args:
        title: Event title
        datetime_str: Event start time (any supported format)
        duration_minutes: Duration in minutes (default: 60)
        attendees: Optional list of email addresses to invite
    
    Returns:
        dict: Created event details, or duplicate_prevented status
    """
    service = get_calendar_service()
    
    # Parse → strip tzinfo → localize as IST (unconditional)
    parsed_dt = parse_datetime(datetime_str)
    start_dt = force_ist(parsed_dt)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    start_iso = start_dt.isoformat()
    
    # Prevent duplicate events
    if is_duplicate_event(service, title, start_iso):
        return {
            'status': 'duplicate_prevented',
            'summary': title,
            'start': start_iso
        }
    
    # Create event — always Asia/Kolkata, with Google Meet
    import uuid
    event = {
        'summary': title,
        'start': {
            'dateTime': start_iso,
            'timeZone': TIMEZONE_NAME,
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': TIMEZONE_NAME,
        },
        'conferenceData': {
            'createRequest': {
                'requestId': uuid.uuid4().hex,
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
                {'method': 'email', 'minutes': 30},
            ]
        },
    }
    
    # Add attendees if provided
    if attendees:
        event['attendees'] = [{'email': email.strip()} for email in attendees if email.strip()]
    
    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()
    
    # Extract Google Meet link from entryPoints
    meet_link = None
    conference_data = created_event.get('conferenceData')
    if conference_data:
        for ep in conference_data.get('entryPoints', []):
            if ep.get('entryPointType') == 'video':
                meet_link = ep.get('uri')
                break
    
    return {
        'event_id': created_event.get('id'),
        'link': created_event.get('htmlLink'),
        'meet_link': meet_link,
        'summary': created_event.get('summary'),
        'start': created_event['start'].get('dateTime'),
        'attendees': [a.get('email') for a in created_event.get('attendees', [])]
    }


def list_upcoming_events(days: int = 1):
    """
    Fetch upcoming calendar events. Uses IST system clock.
    
    Args:
        days: Number of days ahead to look (default: 1)
    
    Returns:
        list[dict]: Events with summary, start, and id
    """
    service = get_calendar_service()
    
    now = datetime.now(IST)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return [
        {
            'summary': event.get('summary', '(No title)'),
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'id': event.get('id')
        }
        for event in events_result.get('items', [])
    ]


def delete_calendar_event(event_id: str):
    """
    Delete a calendar event by its ID.
    
    Args:
        event_id: Google Calendar event ID
    
    Returns:
        dict: Deletion status and deleted event ID
    """
    service = get_calendar_service()
    
    service.events().delete(
        calendarId='primary',
        eventId=event_id
    ).execute()
    
    return {
        'status': 'success',
        'deleted_event_id': event_id
    }


def find_events_by_description(query: str):
    """
    Search upcoming events (next 7 days) for case-insensitive partial matches.
    Results are ordered by start time (nearest future first).
    
    Args:
        query: Natural language phrase to match against event summaries
    
    Returns:
        list[dict]: All matching events with summary, start, and id
    """
    service = get_calendar_service()
    
    now = datetime.now(IST)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=7)).isoformat()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    query_lower = query.strip().lower()
    matches = []
    
    for event in events_result.get('items', []):
        summary = event.get('summary', '')
        if query_lower in summary.lower():
            matches.append({
                'summary': summary,
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'id': event.get('id')
            })
    
    return matches


def delete_event_by_description(query: str):
    """
    Find and delete a calendar event by natural language description.
    
    - Exactly one match  → auto-delete
    - Multiple matches   → return list for user clarification
    - No matches         → return not_found
    
    Args:
        query: Description to search for (e.g. "gym", "dentist", "meeting with Rahul")
    
    Returns:
        dict: Deletion result with status and details
    """
    matches = find_events_by_description(query)
    
    if not matches:
        return {
            'status': 'not_found',
            'message': f"No matching event found for '{query}' in the next 7 days."
        }
    
    if len(matches) == 1:
        # Exactly one match — auto-delete (nearest future, since ordered by startTime)
        event = matches[0]
        service = get_calendar_service()
        service.events().delete(
            calendarId='primary',
            eventId=event['id']
        ).execute()
        
        return {
            'status': 'deleted',
            'deleted_summary': event['summary'],
            'deleted_start': event['start'],
            'deleted_id': event['id']
        }
    
    # Multiple matches — return list for clarification
    return {
        'status': 'multiple_matches',
        'message': f"Found {len(matches)} events matching '{query}'. Please specify which one:",
        'matches': [
            {'summary': m['summary'], 'start': m['start'], 'id': m['id']}
            for m in matches
        ]
    }


def modify_event_by_description(query: str, new_datetime_str: str):
    """
    Find and reschedule a calendar event by natural language description.
    
    - Fuzzy matches event title in the next 7 days
    - Single match → update start/end time, preserve original duration
    - Multiple matches → return list for user clarification
    - No match → return not_found
    
    Args:
        query: Description to identify the event (e.g. "gym", "meeting with Rahul")
        new_datetime_str: New start time in any supported format
    
    Returns:
        dict: Modification result with status and details
    """
    matches = find_events_by_description(query)
    
    if not matches:
        return {
            'status': 'not_found',
            'message': f"No matching event found for '{query}' in the next 7 days."
        }
    
    if len(matches) > 1:
        return {
            'status': 'multiple_matches',
            'message': f"Found {len(matches)} events matching '{query}'. Please specify which one:",
            'matches': [
                {'summary': m['summary'], 'start': m['start'], 'id': m['id']}
                for m in matches
            ]
        }
    
    # Exactly one match — proceed with modification
    event_match = matches[0]
    service = get_calendar_service()
    
    # Fetch full event to get current start/end and preserve duration
    full_event = service.events().get(
        calendarId='primary',
        eventId=event_match['id']
    ).execute()
    
    old_start_str = full_event['start'].get('dateTime')
    old_end_str = full_event['end'].get('dateTime')
    
    # Calculate original duration
    if old_start_str and old_end_str:
        old_start = datetime.fromisoformat(old_start_str)
        old_end = datetime.fromisoformat(old_end_str)
        original_duration = old_end - old_start
    else:
        original_duration = timedelta(minutes=60)
    
    # Parse and localize new start time
    new_start = force_ist(parse_datetime(new_datetime_str))
    new_end = new_start + original_duration
    
    # Patch only the start/end fields
    patch_body = {
        'start': {
            'dateTime': new_start.isoformat(),
            'timeZone': TIMEZONE_NAME,
        },
        'end': {
            'dateTime': new_end.isoformat(),
            'timeZone': TIMEZONE_NAME,
        },
    }
    
    updated_event = service.events().patch(
        calendarId='primary',
        eventId=event_match['id'],
        body=patch_body
    ).execute()
    
    return {
        'status': 'modified',
        'summary': updated_event.get('summary'),
        'old_start': old_start_str,
        'new_start': updated_event['start'].get('dateTime'),
        'new_end': updated_event['end'].get('dateTime'),
        'duration_minutes': int(original_duration.total_seconds() / 60),
        'link': updated_event.get('htmlLink')
    }


def find_free_slots(date_str: str, duration_minutes: int = 30):
    """
    Find free time slots on a given date that can fit the requested duration.
    
    Scans events between 08:00 and 22:00 IST, computes gaps, and returns
    intervals large enough for the requested meeting.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        duration_minutes: Minimum slot length in minutes (default: 30)
    
    Returns:
        dict: Date, requested duration, and list of free slots with start/end/duration
    """
    service = get_calendar_service()
    
    # Parse the target date
    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    
    # Working window: 08:00 – 22:00 IST
    day_start = IST.localize(datetime.combine(target_date, datetime.strptime("08:00", "%H:%M").time()))
    day_end = IST.localize(datetime.combine(target_date, datetime.strptime("22:00", "%H:%M").time()))
    
    # Fetch events for that day
    events_result = service.events().list(
        calendarId='primary',
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # Build list of busy intervals
    busy = []
    for event in events:
        start_str = event['start'].get('dateTime')
        end_str = event['end'].get('dateTime')
        if start_str and end_str:
            busy.append((
                datetime.fromisoformat(start_str),
                datetime.fromisoformat(end_str)
            ))
    
    # Sort by start time (should already be sorted, but be safe)
    busy.sort(key=lambda x: x[0])
    
    # Walk through gaps
    free_slots = []
    cursor = day_start
    
    for busy_start, busy_end in busy:
        # Clamp to working window
        busy_start = max(busy_start, day_start)
        busy_end = min(busy_end, day_end)
        
        if cursor < busy_start:
            gap_minutes = int((busy_start - cursor).total_seconds() / 60)
            if gap_minutes >= duration_minutes:
                free_slots.append({
                    'start': cursor.strftime("%H:%M"),
                    'end': busy_start.strftime("%H:%M"),
                    'duration_minutes': gap_minutes
                })
        
        cursor = max(cursor, busy_end)
    
    # Final gap from last event to end of day
    if cursor < day_end:
        gap_minutes = int((day_end - cursor).total_seconds() / 60)
        if gap_minutes >= duration_minutes:
            free_slots.append({
                'start': cursor.strftime("%H:%M"),
                'end': day_end.strftime("%H:%M"),
                'duration_minutes': gap_minutes
            })
    
    return {
        'date': date_str,
        'requested_duration': duration_minutes,
        'free_slots': free_slots,
        'total_free_slots': len(free_slots)
    }
