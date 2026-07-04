"""Google calendar classification and list helpers (NUMA-104 P3, PLAN 16.1).

Leaf module: stdlib only, no cross-module calendar imports. Extracted verbatim
from calendar/service.py; service.py re-exports these names.
"""
from typing import Any, Dict, List, Optional

WRITABLE_CALENDAR_ACCESS_ROLES = {"owner", "writer"}

# Only the contacts calendar is always excluded (no user-visible events).
# Holiday and birthday calendars are intentionally included for frontend display.
CONTACTS_CALENDAR_MARKER = "#contacts@group.v.calendar.google.com"

# Marker that identifies Google's public holiday calendars
HOLIDAY_CALENDAR_MARKER = "#holiday@group.v.calendar.google.com"

# Keywords that classify a calendar as birthday/anniversary
BIRTHDAY_SUMMARY_KEYWORDS = ("birthday", "birthdays", "anniversar")

# Frontend colour per calendar type
_CALENDAR_TYPE_COLORS: Dict[str, Optional[str]] = {
    "personal":  None,          # use frontend default
    "shared":    "#8B5CF6",     # violet
    "holiday":   "#F59E0B",     # amber / gold
    "birthday":  "#EC4899",     # pink
    "other":     "#6B7280",     # grey
}


# ── Calendar type classification ──────────────────────────────────────────────

def _get_calendar_type(cal: Dict) -> str:
    """
    Classify a Google calendar dict into one of:
      'personal', 'shared', 'holiday', 'birthday', 'other'
    """
    google_cal_id = str(cal.get("id") or "").lower()
    summary       = str(cal.get("summary") or "").lower()
    access_role   = str(cal.get("accessRole") or cal.get("access_role") or "").lower()

    if HOLIDAY_CALENDAR_MARKER in google_cal_id:
        return "holiday"

    if any(kw in summary for kw in ("holiday", "holidays", "festival", "festivals")):
        return "holiday"

    if any(kw in summary for kw in BIRTHDAY_SUMMARY_KEYWORDS):
        return "birthday"

    if access_role in ("owner", "writer") or bool(cal.get("primary")):
        return "personal"

    if access_role in ("reader", "freebusyreader"):
        return "shared"

    return "other"


def _color_for_calendar_type(calendar_type: str) -> Optional[str]:
    """Return the frontend display colour for a calendar type."""
    return _CALENDAR_TYPE_COLORS.get(calendar_type)


# ── Calendar list helpers ─────────────────────────────────────────────────────

def _primary_calendar_entry(service) -> Dict[str, Any]:
    try:
        primary = service.calendarList().get(calendarId="primary").execute()
        if primary:
            primary["primary"] = True
            primary["calendar_type"] = "personal"
            return primary
    except Exception:
        pass

    for cal in list_all_calendars(service):
        if cal.get("primary"):
            cal["calendar_type"] = cal.get("calendar_type") or "personal"
            return cal

    return {
        "id": "primary",
        "summary": "Primary",
        "primary": True,
        "accessRole": "owner",
        "calendar_type": "personal",
    }


def _primary_calendar_ids(service) -> List[str]:
    ids = ["primary"]
    try:
        primary_id = str(_primary_calendar_entry(service).get("id") or "").strip()
        if primary_id and primary_id not in ids:
            ids.append(primary_id)
    except Exception:
        pass
    return ids


def list_all_calendars(service) -> List[Dict[str, Any]]:
    """
    Return ALL user calendars including holidays and birthdays.
    Only the contacts metadata calendar (no user-visible events) is excluded.

    Used for full frontend display; includes colour / type metadata.
    Agent tools use list_selected_calendars() which stays filtered.
    """
    response  = service.calendarList().list().execute()
    calendars: List[Dict[str, Any]] = []

    for cal in response.get("items", []):
        google_cal_id = str(cal.get("id") or "").strip().lower()

        # Contacts calendar has no standalone events - skip always
        if CONTACTS_CALENDAR_MARKER in google_cal_id:
            continue

        cal_type = _get_calendar_type(cal)
        calendars.append(
            {
                "id":            cal.get("id"),
                "summary":       cal.get("summary"),
                "description":   cal.get("description"),
                "time_zone":     cal.get("timeZone"),
                "access_role":   cal.get("accessRole"),
                "selected":      cal.get("selected", True),
                "is_primary":    bool(cal.get("primary")),
                "calendar_type": cal_type,
                "raw_calendar":  cal,
            }
        )

    return calendars


def list_selected_calendars(service) -> List[Dict[str, Any]]:
    """
    Return only user-writeable / subscribed calendars (no holidays/birthdays).
    Used by agent tools that care about the user's own meetings.
    """
    response  = service.calendarList().list().execute()
    calendars: List[Dict[str, Any]] = []

    for cal in response.get("items", []):
        if not _is_supported_user_calendar(cal):
            continue

        calendars.append(
            {
                "id":          cal.get("id"),
                "summary":     cal.get("summary"),
                "description": cal.get("description"),
                "time_zone":   cal.get("timeZone"),
                "access_role": cal.get("accessRole"),
                "selected":    cal.get("selected", True),
                "is_primary":  bool(cal.get("primary")),
                "calendar_type": _get_calendar_type(cal),
                "raw_calendar": cal,
            }
        )

    return calendars


def _is_supported_user_calendar(cal: Dict[str, Any]) -> bool:
    """
    Returns True if the calendar should be included in agent-facing fetches
    (personal writable / primary calendars only, no holidays/birthdays).
    """
    is_primary  = bool(cal.get("primary"))
    selected    = bool(cal.get("selected", True))
    access_role = str(cal.get("accessRole") or "").strip().lower()
    google_cal_id = str(cal.get("id") or "").strip().lower()
    summary       = str(cal.get("summary") or "").strip().lower()

    # Always exclude contacts
    if CONTACTS_CALENDAR_MARKER in google_cal_id:
        return False

    # Exclude holiday and birthday calendars from agent tools
    if HOLIDAY_CALENDAR_MARKER in google_cal_id:
        return False

    if any(kw in summary for kw in ("holiday", "holidays", "festival", "festivals")):
        return False

    if any(kw in summary for kw in BIRTHDAY_SUMMARY_KEYWORDS):
        return False

    if is_primary:
        return True

    if not selected:
        return False

    return access_role in WRITABLE_CALENDAR_ACCESS_ROLES
