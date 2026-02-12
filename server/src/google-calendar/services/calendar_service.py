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
    Check if an event with the same title exists at the same start time.
    
    Args:
        service: Google Calendar API service
        title: Event title to check
        start_iso: ISO formatted start time
    
    Returns:
        bool: True if a duplicate exists
    """
    # Search within a 1-minute window around the start time
    start_dt = datetime.fromisoformat(start_iso)
    time_min = start_dt.isoformat()
    time_max = (start_dt + timedelta(minutes=1)).isoformat()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    for event in events_result.get('items', []):
        if event.get('summary', '').strip().lower() == title.strip().lower():
            return True
    
    return False


def create_calendar_event(title: str, datetime_str: str, duration_minutes: int = 60):
    """
    Create a new calendar event — forced IST, with duplicate prevention.
    
    Args:
        title: Event title
        datetime_str: Event start time (any supported format)
        duration_minutes: Duration in minutes (default: 60)
    
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
    
    # Create event — always Asia/Kolkata
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
    }
    
    created_event = service.events().insert(
        calendarId='primary',
        body=event
    ).execute()
    
    return {
        'event_id': created_event.get('id'),
        'link': created_event.get('htmlLink'),
        'summary': created_event.get('summary'),
        'start': created_event['start'].get('dateTime')
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


def find_event_by_text(search_text: str):
    """
    Search upcoming events (next 7 days) for a case-insensitive match on summary.
    
    Args:
        search_text: Natural language description to match against event summaries
    
    Returns:
        dict or None: First matching event with summary, start, and id — or None
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
    
    search_lower = search_text.strip().lower()
    
    for event in events_result.get('items', []):
        summary = event.get('summary', '')
        if search_lower in summary.lower():
            return {
                'summary': summary,
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'id': event.get('id')
            }
    
    return None


def delete_event_by_text(search_text: str):
    """
    Find and delete a calendar event by natural language description.
    
    Args:
        search_text: Description to search for (e.g. "gym", "dentist", "meeting with Rahul")
    
    Returns:
        dict: Deletion result with status and event summary
    """
    match = find_event_by_text(search_text)
    
    if match is None:
        return {
            'status': 'not_found',
            'message': f"No matching event found for '{search_text}'."
        }
    
    # Delete the matched event
    service = get_calendar_service()
    service.events().delete(
        calendarId='primary',
        eventId=match['id']
    ).execute()
    
    return {
        'status': 'success',
        'deleted_summary': match['summary'],
        'deleted_start': match['start'],
        'deleted_id': match['id']
    }
