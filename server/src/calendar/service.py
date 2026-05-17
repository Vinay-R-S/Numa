"""
Google Calendar service utilities extracted from GoogleCalender-Agent and adapted
for NUMA server modules.

Storage strategy
----------------
All calendar data is persisted in the normalized cal_* tables:

  cal_calendars   - one row per Google calendar per user (incl. holidays/birthdays)
  cal_events      - one row per event, no raw JSON blobs
  cal_attendees   - one row per attendee per event

Cache strategy
--------------
get_events_for_frontend() checks cal_calendars.last_synced_at. If any calendar
was synced within CACHE_TTL_MINUTES, it reads events directly from the DB
instead of hitting the Google API. Pass force_refresh=True to bypass.

This dramatically reduces Google API calls AND means the agent can query
cal_events with SQL instead of re-fetching JSON, saving Groq context tokens.

Calendar types
--------------
  personal  - user's own writeable calendars
  shared    - calendars shared with the user (read-only or limited write)
  holiday   - public holiday / festival calendars
  birthday  - birthday / anniversary calendars
  other     - everything else

The frontend uses calendar_type for colour-coding.
The agent tools use it to filter (e.g. skip holidays when listing meetings).
"""

import os
import uuid
import json
import importlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..db import _get_conn
from ..memory import memory_service
from ..memory.service import (
    store_calendar_event as _qdrant_store_event,
    delete_month_calendar_events as _qdrant_delete_month,
    delete_calendar_event as _qdrant_delete_event,
)
from ..tasks import service as task_service


TIMEZONE_NAME = os.getenv("TIMEZONE", "Asia/Kolkata")
log = logging.getLogger(__name__)
SYNC_WORKERS   = int(os.getenv("CALENDAR_SYNC_WORKERS", "3"))

# How long to consider the DB cache fresh before re-fetching from Google
CACHE_TTL_MINUTES = int(os.getenv("CALENDAR_CACHE_TTL_MINUTES", "30"))

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


# ── Timezone ──────────────────────────────────────────────────────────────────

def _resolve_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(TIMEZONE_NAME)
    except ZoneInfoNotFoundError:
        fallback = "UTC"
        log.warning(
            "Timezone '%s' not found. Falling back to '%s'. Install 'tzdata' to use IANA timezone names on this platform.",
            TIMEZONE_NAME,
            fallback,
        )
        return ZoneInfo(fallback)


TIMEZONE = _resolve_timezone()

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

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]


# ── Google API deps ───────────────────────────────────────────────────────────

def _require_google_calendar_deps():
    try:
        request_module     = importlib.import_module("google.auth.transport.requests")
        credentials_module = importlib.import_module("google.oauth2.credentials")
        flow_module        = importlib.import_module("google_auth_oauthlib.flow")
        discovery_module   = importlib.import_module("googleapiclient.discovery")

        Request     = getattr(request_module,     "Request")
        Credentials = getattr(credentials_module, "Credentials")
        Flow        = getattr(flow_module,        "Flow")
        build       = getattr(discovery_module,   "build")
    except ImportError as exc:
        raise RuntimeError(
            "Google Calendar dependencies are missing. Install google-api-python-client, google-auth, and google-auth-oauthlib."
        ) from exc

    return Request, Credentials, Flow, build


# ── Credentials / path helpers ────────────────────────────────────────────────

def _candidate_credentials_paths() -> List[Path]:
    explicit = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE")
    if explicit:
        return [Path(explicit)]

    workspace_root = Path(__file__).resolve().parents[3]
    return [
        Path.cwd() / "gCalender_credentials.json",
        workspace_root / "server" / "gCalender_credentials.json",
        workspace_root / "GoogleCalender-Agent" / "Backend-agent" / "gCalender_credentials.json",
    ]


def _resolve_credentials_file() -> Path:
    for candidate in _candidate_credentials_paths():
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "Google credentials file not found. Set GOOGLE_CALENDAR_CREDENTIALS_FILE or place gCalender_credentials.json in server/."
    )


def _legacy_token_file() -> Path:
    explicit = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE")
    if explicit:
        return Path(explicit)

    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "server" / "token.json"


def _token_dir() -> Path:
    explicit = os.getenv("GOOGLE_CALENDAR_TOKEN_DIR")
    if explicit:
        return Path(explicit)

    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "server" / "apiConfig" / "google"


def _user_token_file(user_id: str) -> Path:
    safe_user_id = "".join(ch for ch in user_id if ch.isalnum() or ch in ("-", "_"))
    if not safe_user_id:
        raise RuntimeError("Invalid user id for Google token storage")
    return _token_dir() / f"{safe_user_id}.json"


def _load_client_config() -> Dict[str, Any]:
    creds_path = _resolve_credentials_file()
    try:
        config = json.loads(creds_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Google credentials file is not valid JSON") from exc

    if not isinstance(config, dict):
        raise RuntimeError("Google credentials JSON must be an object")
    if "web" not in config and "installed" not in config:
        raise RuntimeError("Google credentials JSON must contain a 'web' client or 'installed' client")

    return config


def has_calendar_credentials(user_id: str) -> bool:
    return _user_token_file(user_id).exists()


def build_google_oauth_authorization_url(redirect_uri: str, state: str) -> str:
    _, _, Flow, _ = _require_google_calendar_deps()

    flow = Flow.from_client_config(_load_client_config(), scopes=GOOGLE_SCOPES, state=state)
    flow.redirect_uri = redirect_uri

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes=False,
        prompt="consent",
    )
    return authorization_url


def exchange_google_oauth_code(user_id: str, code: str, redirect_uri: str) -> None:
    _, _, Flow, _ = _require_google_calendar_deps()

    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    flow = Flow.from_client_config(_load_client_config(), scopes=GOOGLE_SCOPES)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)

    token_path = _user_token_file(user_id)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(flow.credentials.to_json(), encoding="utf-8")


def get_credentials(user_id: Optional[str] = None):
    """
    Load and refresh Google OAuth credentials for *user_id*.

    Raises RuntimeError with a clear message in two failure modes:
    - Token file does not exist  → prompt OAuth start
    - invalid_grant on refresh   → token revoked or app in Testing mode (7-day
      lifetime); stale file is deleted and user must re-authorise
    """
    Request, Credentials, _, _ = _require_google_calendar_deps()

    if user_id:
        token_path = _user_token_file(user_id)
    else:
        token_path = _legacy_token_file()

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as refresh_err:
                err_str = str(refresh_err).lower()
                if "invalid_grant" in err_str or "bad request" in err_str:
                    log.warning(
                        "Google refresh token invalid for user %s - deleting stale token file. "
                        "User must reconnect via OAuth.",
                        user_id,
                    )
                    try:
                        token_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise RuntimeError(
                        "Google Calendar session expired or was revoked. "
                        "Please reconnect your Google account via /calendar/oauth/start."
                    ) from refresh_err
                raise RuntimeError(f"Failed to refresh Google token: {refresh_err}") from refresh_err
        else:
            raise RuntimeError(
                "Google Calendar is not connected for this account. Start OAuth via /calendar/oauth/start."
            )

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _get_user_email(user_id: Optional[str]) -> str:
    """
    Read the authenticated Google user's email from the stored token JSON.
    Returns empty string if unavailable (non-fatal - used only for Qdrant payload).
    """
    if not user_id:
        return ""
    try:
        token_path = _user_token_file(user_id)
        if not token_path.exists():
            return ""
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
        # The id_token inside the token JSON contains the email as a claim
        # but it's simpler to just read the 'token_uri' owner claim if available.
        # Fallback: try 'client_id' prefix or return empty.
        return str(token_data.get("client_email") or token_data.get("email") or "")
    except Exception:
        return ""


def get_all_connected_user_ids() -> List[str]:
    """
    Return a list of all user_ids that have a valid Google Calendar token on disk.
    Used by the nightly scheduler to sync every connected user.
    """
    token_dir = _token_dir()
    if not token_dir.exists():
        return []
    user_ids: List[str] = []
    for token_file in token_dir.glob("*.json"):
        user_id = token_file.stem  # filename without .json is the user_id
        if user_id:
            user_ids.append(user_id)
    return user_ids


def get_calendar_service(user_id: Optional[str] = None):
    _, _, _, build = _require_google_calendar_deps()
    creds = get_credentials(user_id=user_id)
    return build("calendar", "v3", credentials=creds)


# ── Datetime helpers ──────────────────────────────────────────────────────────

def parse_datetime(datetime_str: str) -> datetime:
    cleaned = datetime_str.strip().rstrip(".")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1]

    natural_prefixes = {"today": 0, "tomorrow": 1, "tmr": 1}

    lower = cleaned.lower()
    for prefix, day_offset in natural_prefixes.items():
        if lower.startswith(prefix):
            remainder = cleaned[len(prefix):].lstrip("T").lstrip("t").lstrip()
            now = datetime.now(TIMEZONE)
            base_date = (now + timedelta(days=day_offset)).date()

            if not remainder:
                return datetime.combine(base_date, datetime.min.time())

            for time_fmt in ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]:
                try:
                    parsed_time = datetime.strptime(remainder, time_fmt).time()
                    return datetime.combine(base_date, parsed_time)
                except ValueError:
                    continue

            raise ValueError(f"Could not parse time portion '{remainder}' from '{datetime_str}'.")

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        pass

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    raise ValueError(
        f"Could not parse datetime '{datetime_str}'. Supported formats include YYYY-MM-DDTHH:MM:SS and YYYY-MM-DD HH:MM."
    )


def force_local(dt: datetime) -> datetime:
    naive = dt.replace(tzinfo=None)
    return naive.replace(tzinfo=TIMEZONE)


def _to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TIMEZONE)
    return dt.astimezone(TIMEZONE)


def _iso_to_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_calendar_event_id(event_id: str) -> Tuple[str, str]:
    if ":" in event_id:
        cal_id, actual_event_id = event_id.split(":", 1)
        return cal_id, actual_event_id
    return "primary", event_id


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


def _persist_mutated_event(user_id: Optional[str], service, event: Dict) -> None:
    if not user_id:
        return

    google_cal_id = str(event.get("_calendar_id") or "primary")
    cal = _primary_calendar_entry(service) if google_cal_id == "primary" else {
        "id": google_cal_id,
        "summary": event.get("_calendar_summary") or google_cal_id,
        "accessRole": event.get("_calendar_access_role") or "owner",
        "calendar_type": event.get("_calendar_type") or "personal",
    }

    cal_type = str(cal.get("calendar_type") or event.get("_calendar_type") or "personal")
    calendar_uuid = _ensure_cal_calendar(user_id, cal, calendar_type=cal_type)
    stored_event = dict(event)
    stored_event["_calendar_id"] = str(cal.get("id") or google_cal_id)
    stored_event["_calendar_summary"] = cal.get("summary") or event.get("_calendar_summary") or "Primary"
    stored_event["_calendar_access_role"] = cal.get("accessRole") or cal.get("access_role") or "owner"
    stored_event["_calendar_type"] = cal_type
    _store_cal_event(user_id, calendar_uuid, stored_event)


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


def _event_datetime_bounds(event: Dict) -> Tuple[datetime, datetime, bool, Optional[str], Optional[str]]:
    start_data = event.get("start", {})
    end_data   = event.get("end",   {})

    start_dt_raw = start_data.get("dateTime")
    end_dt_raw   = end_data.get("dateTime")

    if start_dt_raw and end_dt_raw:
        start_at = _iso_to_datetime(start_dt_raw)
        end_at   = _iso_to_datetime(end_dt_raw)
        return start_at, end_at, False, start_data.get("timeZone"), end_data.get("timeZone")

    start_date_raw = start_data.get("date")
    end_date_raw   = end_data.get("date")

    if not start_date_raw:
        now = datetime.now(TIMEZONE)
        return now, now + timedelta(hours=1), False, TIMEZONE_NAME, TIMEZONE_NAME

    start_at = datetime.fromisoformat(f"{start_date_raw}T00:00:00").replace(tzinfo=TIMEZONE)
    if end_date_raw:
        end_at = datetime.fromisoformat(f"{end_date_raw}T00:00:00").replace(tzinfo=TIMEZONE)
    else:
        end_at = start_at + timedelta(days=1)

    if end_at <= start_at:
        end_at = start_at + timedelta(days=1)

    return start_at, end_at, True, start_data.get("timeZone") or TIMEZONE_NAME, end_data.get("timeZone") or TIMEZONE_NAME


# ── Current-month window helpers ──────────────────────────────────────────────

def _current_month_window() -> Tuple[datetime, datetime]:
    """Return (month_start, month_end_exclusive) for the current calendar month."""
    now = datetime.now(TIMEZONE)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        month_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        month_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start, month_end


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


# ══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER - read from cal_events DB before hitting Google API
# ══════════════════════════════════════════════════════════════════════════════

def _is_cache_fresh_for_month(user_id: str, month_start: datetime, month_end: datetime) -> bool:
    """
    Return True if:
    1. At least one cal_calendar exists for this user, AND
    2. The most recently synced calendar was synced within CACHE_TTL_MINUTES, AND
    3. There is at least one cal_event within the current month window.

    This avoids hitting the Google API on every page load.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Check latest sync timestamp
        cur.execute(
            """
            SELECT MAX(last_synced_at), COUNT(*)
            FROM public.cal_calendars
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row or not row[0] or not row[1]:
            cur.close()
            return False

        latest_sync: datetime = row[0]
        cutoff = datetime.now(TIMEZONE) - timedelta(minutes=CACHE_TTL_MINUTES)

        if _to_local(latest_sync) < cutoff:
            cur.close()
            return False

        # Check that there are events in the month window
        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.cal_events
            WHERE user_id = %s
              AND start_at >= %s
              AND start_at <  %s
              AND deleted_at IS NULL
            """,
            (user_id, month_start, month_end),
        )
        count_row = cur.fetchone()
        cur.close()
        return bool(count_row and count_row[0] and count_row[0] > 0)

    except Exception as exc:
        log.warning("Cache freshness check failed: %s", exc)
        return False
    finally:
        conn.close()


def _read_month_events_from_db(user_id: str, month_start: datetime, month_end: datetime) -> List[Dict]:
    """
    Read all active cal_events for the current month from the DB and format
    them for the frontend. No Google API call needed.

    This is the Groq-token-saving path: the agent can also call SQL against
    cal_events instead of re-fetching JSON from Google.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                e.google_event_id,
                e.title,
                e.description,
                e.start_at,
                e.end_at,
                e.is_all_day,
                e.is_readonly,
                e.meet_link,
                e.html_link,
                e.recurring_event_id,
                c.name          AS calendar_name,
                c.google_cal_id AS google_cal_id,
                c.calendar_type AS calendar_type,
                c.access_role   AS access_role
            FROM public.cal_events e
            JOIN public.cal_calendars c ON c.id = e.calendar_id
            WHERE e.user_id     = %s
              AND e.start_at   >= %s
              AND e.start_at   <  %s
              AND e.deleted_at IS NULL
            ORDER BY e.start_at
            """,
            (user_id, month_start, month_end),
        )

        rows = cur.fetchall() or []
        cols = [desc[0] for desc in (cur.description or [])]
        cur.close()

        results: List[Dict] = []
        for row in rows:
            r = dict(zip(cols, row))

            start_local = _to_local(r["start_at"])
            end_local   = _to_local(r["end_at"])
            is_all_day  = bool(r["is_all_day"])

            start_time = "00:00" if is_all_day else start_local.strftime("%H:%M")
            end_time   = "23:59" if is_all_day else end_local.strftime("%H:%M")

            cal_type    = r.get("calendar_type") or "personal"
            is_readonly = bool(r["is_readonly"])
            google_cal_id   = r["google_cal_id"]
            google_event_id = r["google_event_id"]
            safe_id = google_event_id if not is_readonly else f"{google_cal_id}:{google_event_id}"

            description = r.get("description") or ""
            if not description and r.get("calendar_name"):
                description = f"From {r['calendar_name']}"

            results.append(
                {
                    "id":          safe_id,
                    "title":       r["title"] or "(No title)",
                    "date":        start_local.date().isoformat(),
                    "startTime":   start_time,
                    "endTime":     end_time,
                    "description": description,
                    "color":       _color_for_calendar_type(cal_type),
                    "calendarName": r.get("calendar_name"),
                    "readonly":    is_readonly,
                }
            )

        return results

    except Exception as exc:
        log.warning("Failed to read month events from DB: %s", exc)
        return []
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZED STORAGE - cal_calendars / cal_events / cal_attendees
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_cal_calendar(user_id: str, cal: Dict, calendar_type: str = "personal") -> str:
    """
    Upsert a row into cal_calendars and return its UUID (as string).
    """
    google_cal_id = str(cal.get("id") or "").strip()
    if not google_cal_id:
        raise ValueError("Calendar dict is missing 'id'")

    name        = str(cal.get("summary") or google_cal_id).strip() or google_cal_id
    access_role = str(cal.get("access_role") or cal.get("accessRole") or "reader").strip()
    if access_role not in ("owner", "writer", "reader", "freeBusyReader"):
        access_role = "reader"
    is_primary = bool(cal.get("is_primary") or cal.get("primary"))

    # Validate calendar_type
    if calendar_type not in ("personal", "shared", "holiday", "birthday", "other"):
        calendar_type = "other"

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.cal_calendars
                (user_id, google_cal_id, name, access_role, is_primary, calendar_type, last_synced_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id, google_cal_id)
            DO UPDATE SET
                name           = EXCLUDED.name,
                access_role    = EXCLUDED.access_role,
                is_primary     = EXCLUDED.is_primary,
                calendar_type  = EXCLUDED.calendar_type,
                last_synced_at = NOW(),
                updated_at     = NOW()
            RETURNING id
            """,
            (user_id, google_cal_id, name, access_role, is_primary, calendar_type),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return str(row[0])
    except Exception as exc:
        log.warning("Failed to upsert cal_calendar(%s, %s): %s", user_id, google_cal_id, exc)
        raise
    finally:
        conn.close()


def _upsert_cal_event(user_id: str, calendar_uuid: str, event: Dict) -> Optional[str]:
    """
    Upsert one row into cal_events.
    Returns the row UUID so the caller can link attendees, or None on failure.
    """
    google_event_id = str(event.get("id") or "").strip()
    if not google_event_id:
        return None

    start_at, end_at, is_all_day, start_tz, end_tz = _event_datetime_bounds(event)
    status = str(event.get("status") or "confirmed").lower()
    if status not in ("confirmed", "tentative", "cancelled"):
        status = "confirmed"

    organizer      = event.get("organizer") if isinstance(event.get("organizer"), dict) else {}
    organizer_email = organizer.get("email")
    organizer_name  = organizer.get("displayName")
    is_readonly = event.get("_calendar_access_role") not in (None, "owner", "writer")
    deleted_at  = datetime.now(TIMEZONE) if status == "cancelled" else None

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.cal_events (
                calendar_id, user_id, google_event_id,
                title, description, location,
                start_at, end_at, is_all_day, start_time_zone, end_time_zone,
                status, etag, recurring_event_id,
                html_link, meet_link,
                organizer_email, organizer_name,
                is_readonly, deleted_at
            )
            VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
            ON CONFLICT (calendar_id, google_event_id)
            DO UPDATE SET
                title              = EXCLUDED.title,
                description        = EXCLUDED.description,
                location           = EXCLUDED.location,
                start_at           = EXCLUDED.start_at,
                end_at             = EXCLUDED.end_at,
                is_all_day         = EXCLUDED.is_all_day,
                start_time_zone    = EXCLUDED.start_time_zone,
                end_time_zone      = EXCLUDED.end_time_zone,
                status             = EXCLUDED.status,
                etag               = EXCLUDED.etag,
                recurring_event_id = EXCLUDED.recurring_event_id,
                html_link          = EXCLUDED.html_link,
                meet_link          = EXCLUDED.meet_link,
                organizer_email    = EXCLUDED.organizer_email,
                organizer_name     = EXCLUDED.organizer_name,
                is_readonly        = EXCLUDED.is_readonly,
                deleted_at         = EXCLUDED.deleted_at,
                updated_at         = NOW()
            RETURNING id
            """,
            (
                calendar_uuid, user_id, google_event_id,
                str(event.get("summary") or "(No title)").strip() or "(No title)",
                event.get("description"),
                event.get("location"),
                start_at, end_at, is_all_day, start_tz, end_tz,
                status,
                event.get("etag"),
                event.get("recurringEventId"),
                event.get("htmlLink"),
                _extract_meet_link(event),
                organizer_email, organizer_name,
                is_readonly, deleted_at,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return str(row[0]) if row else None
    except Exception as exc:
        log.warning("Failed to upsert cal_event(%s): %s", google_event_id, exc)
        return None
    finally:
        conn.close()


def _upsert_cal_attendees(event_uuid: str, attendees_raw: Any) -> None:
    """
    Parse attendees list from a Google event and upsert into cal_attendees.
    One row per attendee - no JSON blobs - so the agent can query RSVP status
    with plain SQL instead of re-fetching from Google.
    """
    if not isinstance(attendees_raw, list) or not attendees_raw:
        return

    conn = _get_conn()
    try:
        cur = conn.cursor()
        for att in attendees_raw:
            if not isinstance(att, dict):
                continue
            email = str(att.get("email") or "").strip()
            if not email:
                continue

            response_status = str(att.get("responseStatus") or "needsAction")
            if response_status not in ("needsAction", "accepted", "declined", "tentative"):
                response_status = "needsAction"

            cur.execute(
                """
                INSERT INTO public.cal_attendees
                    (event_id, email, display_name, response_status,
                     is_organizer, is_self, optional)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id, email)
                DO UPDATE SET
                    display_name    = EXCLUDED.display_name,
                    response_status = EXCLUDED.response_status,
                    is_organizer    = EXCLUDED.is_organizer,
                    is_self         = EXCLUDED.is_self,
                    optional        = EXCLUDED.optional,
                    updated_at      = NOW()
                """,
                (
                    event_uuid,
                    email,
                    att.get("displayName"),
                    response_status,
                    bool(att.get("organizer")),
                    bool(att.get("self")),
                    bool(att.get("optional")),
                ),
            )

        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to upsert cal_attendees for event %s: %s", event_uuid, exc)
    finally:
        conn.close()


def _store_cal_event(user_id: str, calendar_uuid: str, event: Dict) -> None:
    """Persist one Google event dict to the normalized cal_events + cal_attendees tables,
    then ingest its embedding into the Qdrant calendar collection."""
    event_uuid = _upsert_cal_event(user_id, calendar_uuid, event)
    if not event_uuid:
        return
    _upsert_cal_attendees(event_uuid, event.get("attendees") or [])

    # ── Qdrant ingest (best-effort, non-blocking) ──────────────────────────────
    try:
        google_event_id = str(event.get("id")             or "").strip()
        google_cal_id   = str(event.get("_calendar_id")   or "primary")
        cal_type        = str(event.get("_calendar_type") or "personal")
        title           = str(event.get("summary")        or "(No title)").strip()
        description     = event.get("description")
        start_at, end_at, is_all_day, _, _ = _event_datetime_bounds(event)

        # Resolve the user's Google email from the token file (cached per call)
        user_email = _get_user_email(user_id)

        if google_event_id:
            _qdrant_store_event(
                user_id=user_id,
                user_email=user_email,
                calendar_id=google_cal_id,
                event_id=google_event_id,
                title=title,
                description=description,
                start_at=start_at,
                end_at=end_at,
                is_all_day=is_all_day,
                calendar_type=cal_type,
            )
    except Exception as exc:
        log.warning("Qdrant ingest failed for event (non-fatal): %s", exc)


def _prune_cal_events_outside_month(
    user_id: str,
    month_start: datetime,
    month_end:   datetime,
) -> None:
    """
    Delete cal_events (and cascaded attendees) outside the current month window,
    then clean up linked tasks, memory snapshots, and Qdrant calendar vectors.
    """
    conn   = _get_conn()
    stale: List[Tuple[str, str, str]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.id, c.google_cal_id, e.google_event_id
            FROM public.cal_events e
            JOIN public.cal_calendars c ON c.id = e.calendar_id
            WHERE e.user_id    = %s
              AND (e.start_at < %s OR e.start_at >= %s)
              AND e.deleted_at IS NULL
            """,
            (user_id, month_start, month_end),
        )
        stale = [(str(r[0]), str(r[1]), str(r[2])) for r in (cur.fetchall() or [])]

        if stale:
            ids = [r[0] for r in stale]
            cur.execute(
                "DELETE FROM public.cal_events WHERE id = ANY(%s::uuid[])",
                (ids,),
            )

        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to prune cal_events outside month: %s", exc)
    finally:
        conn.close()

    for _evt_uuid, cal_id, event_id in stale:
        ext_ref = task_service.calendar_external_ref(cal_id, event_id)
        _run_parallel_best_effort(
            lambda r=ext_ref: task_service.delete_task_by_external_ref(user_id, r),
            lambda c=cal_id, e=event_id: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{c}:{e}",
            ),
        )

    # Also purge the previous month's Qdrant calendar vectors
    prev_month_str = (month_start - timedelta(days=1)).strftime("%Y-%m")
    try:
        _qdrant_delete_month(user_id, prev_month_str)
    except Exception as exc:
        log.warning("Qdrant month purge failed for %s/%s: %s", user_id, prev_month_str, exc)


def _reconcile_deleted_events_for_month(
    user_id: str,
    month_start: datetime,
    month_end: datetime,
    fetched_calendar_ids: Set[str],
    active_events: Set[Tuple[str, str]],
) -> None:
    """
    Mark DB events as cancelled when a successful Google fetch no longer
    returns them. This keeps Supabase, frontend cache, tasks, and Qdrant in
    sync with deletes made by the agent or directly in Google Calendar.
    """
    if not fetched_calendar_ids:
        return

    stale: List[Tuple[str, str]] = []
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.google_cal_id, e.google_event_id
            FROM public.cal_events e
            JOIN public.cal_calendars c ON c.id = e.calendar_id
            WHERE e.user_id = %s
              AND e.start_at >= %s
              AND e.start_at < %s
              AND e.deleted_at IS NULL
              AND c.google_cal_id = ANY(%s)
            """,
            (user_id, month_start, month_end, list(fetched_calendar_ids)),
        )
        for cal_id, event_id in cur.fetchall() or []:
            key = (str(cal_id), str(event_id))
            if key not in active_events:
                stale.append(key)

        if stale:
            for cal_id, event_id in stale:
                cur.execute(
                    """
                    UPDATE public.cal_events e
                    SET status = 'cancelled', deleted_at = NOW(), updated_at = NOW()
                    FROM public.cal_calendars c
                    WHERE e.calendar_id = c.id
                      AND e.user_id = %s
                      AND c.google_cal_id = %s
                      AND e.google_event_id = %s
                    """,
                    (user_id, cal_id, event_id),
                )

        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to reconcile deleted calendar events: %s", exc)
        conn.rollback()
    finally:
        conn.close()

    for cal_id, event_id in stale:
        ext_ref = task_service.calendar_external_ref(cal_id, event_id)
        _run_parallel_best_effort(
            lambda r=ext_ref: task_service.delete_task_by_external_ref(user_id, r),
            lambda c=cal_id, e=event_id: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{c}:{e}",
            ),
            lambda e=event_id: _qdrant_delete_event(user_id, e),
        )


# ── Legacy task / memory sync helpers ──────────────────────────────────────────

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

    ical_uid    = str(event.get("iCalUID")         or "").strip()
    event_id    = str(event.get("id")              or "").strip()
    calendar_id = str(event.get("_calendar_id")    or "primary")

    if not ical_uid and not event_id:
        return

    external_ref = f"gcal:ical:{ical_uid}" if ical_uid else task_service.calendar_external_ref(calendar_id, event_id)

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
            pass

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


# ── Google Calendar API helpers ───────────────────────────────────────────────

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


# ── Main frontend fetch (with cache) ─────────────────────────────────────────

def get_events_for_frontend(
    user_id: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Dict]:
    """
    Return all events for the current calendar month, including holidays and
    birthdays, colour-coded by calendar type.

    Cache behaviour
    ---------------
    If the DB cache is fresh (last_synced_at < CACHE_TTL_MINUTES ago) AND
    there are events in the DB, serve from cal_events - no Google API call.
    Pass force_refresh=True (or ?refresh=true on the endpoint) to bypass.

    This saves both Google API quota and Groq context tokens, because the
    Master Agent can query cal_events with SQL instead of sending raw JSON.
    """
    month_start, month_end = _current_month_window()

    # ── Try DB cache first ────────────────────────────────────────────────────
    if user_id and not force_refresh:
        if _is_cache_fresh_for_month(user_id, month_start, month_end):
            cached = _read_month_events_from_db(user_id, month_start, month_end)
            if cached:
                log.debug("Serving calendar from DB cache for user %s", user_id)
                return cached

    # ── Full Google API fetch ─────────────────────────────────────────────────
    service = get_calendar_service(user_id=user_id)

    # Include ALL calendars (holidays, birthdays, personal)
    all_calendars = list_all_calendars(service)

    time_min = month_start.isoformat()
    time_max = month_end.isoformat()

    # Build UUID map: google_cal_id → (cal_uuid, cal_type)
    cal_uuid_map: Dict[str, Tuple[str, str]] = {}
    if user_id:
        for cal in all_calendars:
            try:
                cal_type = cal.get("calendar_type") or "personal"
                cal_uuid = _ensure_cal_calendar(user_id, cal, calendar_type=cal_type)
                cal_uuid_map[str(cal.get("id") or "")] = (cal_uuid, cal_type)
            except Exception as exc:
                log.warning("Could not upsert cal_calendar: %s", exc)

    # Prune events outside the current month
    if user_id:
        _prune_cal_events_outside_month(user_id, month_start, month_end)

    # Fetch from Google (all calendars, type-aware filtering)
    fetched_calendar_ids: Set[str] = set()
    events_raw = fetch_events_across_selected_calendars(
        service,
        time_min,
        time_max,
        selected_calendars=all_calendars,
        fetched_calendar_ids=fetched_calendar_ids,
    )

    # Persist + sync to tasks (personal only)
    if user_id:
        active_events: Set[Tuple[str, str]] = set()
        for event in events_raw:
            google_cal_id = str(event.get("_calendar_id") or "primary")
            google_event_id = str(event.get("id") or "").strip()
            if google_event_id:
                active_events.add((google_cal_id, google_event_id))
            cal_info = cal_uuid_map.get(google_cal_id)
            if cal_info:
                cal_uuid, _ = cal_info
                _store_cal_event(user_id, cal_uuid, event)
            _sync_calendar_event_to_task(user_id, event)
        _reconcile_deleted_events_for_month(
            user_id,
            month_start,
            month_end,
            fetched_calendar_ids,
            active_events,
        )

    return [_format_event_for_frontend(event) for event in events_raw]


# ── Agent-facing fetches (no cache, no holidays, lean format) ─────────────────

def get_events_on_date(date_str: str, user_id: Optional[str] = None) -> List[Dict]:
    """
    Return a slim list of events on a specific date.
    Reads from DB first (Groq-token-friendly); falls back to Google API.
    """
    try:
        target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        day_start   = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=TIMEZONE)
        day_end     = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=TIMEZONE)

        # Try DB read - only personal events for the agent
        if user_id:
            conn = _get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT e.google_event_id, e.title, e.start_at, c.name, c.google_cal_id, c.calendar_type
                    FROM public.cal_events e
                    JOIN public.cal_calendars c ON c.id = e.calendar_id
                    WHERE e.user_id     = %s
                      AND e.start_at   >= %s
                      AND e.start_at   <= %s
                      AND e.deleted_at IS NULL
                      AND c.calendar_type IN ('personal', 'shared')
                    ORDER BY e.start_at
                    """,
                    (user_id, day_start, day_end),
                )
                rows = cur.fetchall() or []
                cur.close()
                if rows:
                    return [
                        {
                            "summary":  r[1],
                            "start":    _to_local(r[2]).isoformat(),
                            "id":       r[0],
                            "calendar": r[3],
                        }
                        for r in rows
                    ]
            except Exception:
                pass
            finally:
                conn.close()
    except Exception:
        pass

    # Fallback: Google API
    service = get_calendar_service(user_id=user_id)
    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    day_start   = datetime.combine(target_date, datetime.strptime("00:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)
    day_end     = datetime.combine(target_date, datetime.strptime("23:59", "%H:%M").time()).replace(tzinfo=TIMEZONE)

    events = fetch_events_across_selected_calendars(
        service, day_start.isoformat(), day_end.isoformat(),
        selected_calendars=list_selected_calendars(service),
    )
    return [
        {
            "summary":  event.get("summary", "(No title)"),
            "start":    event["start"].get("dateTime", event["start"].get("date")),
            "id":       event.get("id"),
            "calendar": event.get("_calendar_summary", "Primary"),
        }
        for event in events
    ]


def list_events_in_window(
    lookback_days: int = 7,
    lookahead_days: int = 8,
    user_id: Optional[str] = None,
) -> List[Dict]:
    """
    List personal events in a window around now.
    Reads from DB when possible; falls back to Google API.
    Used by the AI agent tools (holidays excluded).
    """
    now         = datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today_start - timedelta(days=lookback_days)
    window_end   = today_start + timedelta(days=lookahead_days + 1)

    # Try DB first
    if user_id:
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT e.google_event_id, e.title, e.start_at, c.name, c.google_cal_id
                FROM public.cal_events e
                JOIN public.cal_calendars c ON c.id = e.calendar_id
                WHERE e.user_id     = %s
                  AND e.start_at   >= %s
                  AND e.start_at   <  %s
                  AND e.deleted_at IS NULL
                  AND c.calendar_type IN ('personal', 'shared')
                ORDER BY e.start_at
                """,
                (user_id, window_start, window_end),
            )
            rows = cur.fetchall() or []
            cur.close()
            if rows:
                return [
                    {
                        "summary":  r[1],
                        "start":    _to_local(r[2]).isoformat(),
                        "id":       r[0],
                        "calendar": r[3],
                    }
                    for r in rows
                ]
        except Exception:
            pass
        finally:
            conn.close()

    # Fallback: Google API
    service = get_calendar_service(user_id=user_id)
    time_min = window_start.isoformat()
    time_max = window_end.isoformat()
    events   = fetch_events_across_selected_calendars(
        service, time_min, time_max,
        selected_calendars=list_selected_calendars(service),
    )
    return [
        {
            "summary":  event.get("summary", "(No title)"),
            "start":    event["start"].get("dateTime", event["start"].get("date")),
            "id":       event.get("id"),
            "calendar": event.get("_calendar_summary", "Primary"),
        }
        for event in events
    ]


# ── Event mutations (create / update / delete) ────────────────────────────────

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


def create_event_from_payload(payload, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    body    = _build_google_event_body(payload)
    created = service.events().insert(calendarId="primary", body=body).execute()
    created["_calendar_id"]         = "primary"
    created["_calendar_type"]       = "personal"
    created.setdefault("_calendar_summary", "Primary")
    created.setdefault("status", "confirmed")
    _persist_mutated_event(user_id, service, created)
    _sync_calendar_event_to_task(user_id, created)
    return _format_event_for_frontend(created)


def update_event_from_payload(event_id: str, payload, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)
    body    = _build_google_event_body(payload)
    updated = (
        service.events()
        .patch(calendarId=calendar_id, eventId=actual_event_id, body=body)
        .execute()
    )
    updated["_calendar_id"]         = calendar_id
    updated["_calendar_type"]       = "personal"
    updated.setdefault("_calendar_summary", "Primary")
    updated.setdefault("status", "confirmed")
    _persist_mutated_event(user_id, service, updated)
    _sync_calendar_event_to_task(user_id, updated)
    return _format_event_for_frontend(updated)


def delete_event_by_id(event_id: str, user_id: Optional[str] = None) -> None:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)

    try:
        service.events().delete(calendarId=calendar_id, eventId=actual_event_id).execute()
    except Exception as exc:
        # HTTP 410 Gone means the event was already deleted on Google's side.
        # Treat as success and proceed with local DB / task / Qdrant cleanup.
        err_str = str(exc)
        if "410" in err_str or "Resource has been deleted" in err_str:
            log.info(
                "Event %s/%s already deleted on Google (410) - proceeding with local cleanup.",
                calendar_id, actual_event_id,
            )
        else:
            raise  # Re-raise unexpected errors

    # Always clean up PostgreSQL, tasks, and Qdrant regardless of Google's response
    _delete_cal_event_cleanup(user_id, calendar_id, actual_event_id)



def _delete_cal_event_cleanup(
    user_id: Optional[str],
    google_cal_id: str,
    google_event_id: str,
) -> None:
    """Soft-delete in cal_events and clean up tasks + memory."""
    if not user_id:
        return

    ical_uid: Optional[str] = None
    resolved_calendar_ids = [google_cal_id]
    try:
        service  = get_calendar_service(user_id=user_id)
        if google_cal_id == "primary":
            resolved_calendar_ids = _primary_calendar_ids(service)
        event    = service.events().get(calendarId=google_cal_id, eventId=google_event_id).execute()
        ical_uid = str(event.get("iCalUID") or "").strip() or None
    except Exception:
        pass

    resolved_calendar_ids = list(dict.fromkeys([cid for cid in resolved_calendar_ids if cid]))

    external_ref = (
        f"gcal:ical:{ical_uid}"
        if ical_uid
        else task_service.calendar_external_ref(google_cal_id, google_event_id)
    )
    external_refs = {external_ref}
    for cal_id in resolved_calendar_ids:
        external_refs.add(task_service.calendar_external_ref(cal_id, google_event_id))

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE public.cal_events e
            SET status = 'cancelled', deleted_at = NOW(), updated_at = NOW()
            FROM public.cal_calendars c
            WHERE e.calendar_id      = c.id
              AND c.user_id          = %s
              AND c.google_cal_id    = ANY(%s)
              AND e.google_event_id  = %s
            """,
            (user_id, resolved_calendar_ids, google_event_id),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to soft-delete cal_event: %s", exc)
    finally:
        conn.close()

    _run_parallel_best_effort(
        *[
            (lambda r=ref: task_service.delete_task_by_external_ref(user_id, r))
            for ref in external_refs
        ],
        *[
            (lambda c=cal_id: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{c}:{google_event_id}",
            ))
            for cal_id in resolved_calendar_ids
        ],
        lambda: _qdrant_delete_event(user_id, google_event_id),
    )


# ── Agent-facing helpers (create / modify / delete by description) ────────────

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
