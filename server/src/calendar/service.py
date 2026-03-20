"""
Google Calendar service utilities extracted from GoogleCalender-Agent and adapted
for NUMA server modules.
"""

import os
import uuid
import json
import importlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..db import _get_conn
from ..memory import memory_service
from ..tasks import service as task_service


TIMEZONE_NAME = os.getenv("TIMEZONE", "Asia/Kolkata")
log = logging.getLogger(__name__)
SYNC_WORKERS = int(os.getenv("CALENDAR_SYNC_WORKERS", "3"))
CALENDAR_FRONTEND_WINDOW_DAYS = 8  # Fetch up to 8 days ahead
CALENDAR_FRONTEND_LOOKBACK_DAYS = 7  # Keep past 7 days (auto-delete 8+ days old)
WRITABLE_CALENDAR_ACCESS_ROLES = {"owner", "writer"}
EXCLUDED_CALENDAR_ID_MARKERS = (
    "#holiday@group.v.calendar.google.com",
    "#contacts@group.v.calendar.google.com",
)
EXCLUDED_CALENDAR_SUMMARY_MARKERS = (
    "holiday",
    "holidays",
    "festival",
    "festivals",
    "birthday",
    "birthdays",
)


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


def _require_google_calendar_deps():
    try:
        request_module = importlib.import_module("google.auth.transport.requests")
        credentials_module = importlib.import_module("google.oauth2.credentials")
        flow_module = importlib.import_module("google_auth_oauthlib.flow")
        discovery_module = importlib.import_module("googleapiclient.discovery")

        Request = getattr(request_module, "Request")
        Credentials = getattr(credentials_module, "Credentials")
        Flow = getattr(flow_module, "Flow")
        build = getattr(discovery_module, "build")
    except ImportError as exc:
        raise RuntimeError(
            "Google Calendar dependencies are missing. Install google-api-python-client, google-auth, and google-auth-oauthlib."
        ) from exc

    return Request, Credentials, Flow, build


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
    return workspace_root / "server" / "google_tokens"


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

    # Google may return additional identity scopes (openid/profile/email) during
    # consent; allow this so token exchange does not fail on strict scope checks.
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    flow = Flow.from_client_config(_load_client_config(), scopes=GOOGLE_SCOPES)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)

    token_path = _user_token_file(user_id)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(flow.credentials.to_json(), encoding="utf-8")


def get_credentials(user_id: Optional[str] = None):
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
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "Google Calendar is not connected for this account. Start OAuth via /calendar/oauth/start."
            )

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_calendar_service(user_id: Optional[str] = None):
    _, _, _, build = _require_google_calendar_deps()
    creds = get_credentials(user_id=user_id)
    return build("calendar", "v3", credentials=creds)


def parse_datetime(datetime_str: str) -> datetime:
    cleaned = datetime_str.strip().rstrip(".")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1]

    natural_prefixes = {
        "today": 0,
        "tomorrow": 1,
        "tmr": 1,
    }

    lower = cleaned.lower()
    for prefix, day_offset in natural_prefixes.items():
        if lower.startswith(prefix):
            remainder = cleaned[len(prefix) :].lstrip("T").lstrip("t").lstrip()
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


def _json(value: Any):
    try:
        from psycopg2.extras import Json  # type: ignore

        return Json(value)
    except Exception:
        return json.dumps(value)


def _extract_meet_link(event: Dict) -> Optional[str]:
    conference_data = event.get("conferenceData") or {}
    for entry_point in conference_data.get("entryPoints", []):
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri")
    return None


def _event_datetime_bounds(event: Dict) -> Tuple[datetime, datetime, bool, Optional[str], Optional[str]]:
    start_data = event.get("start", {})
    end_data = event.get("end", {})

    start_dt_raw = start_data.get("dateTime")
    end_dt_raw = end_data.get("dateTime")

    if start_dt_raw and end_dt_raw:
        start_at = _iso_to_datetime(start_dt_raw)
        end_at = _iso_to_datetime(end_dt_raw)
        return start_at, end_at, False, start_data.get("timeZone"), end_data.get("timeZone")

    start_date_raw = start_data.get("date")
    end_date_raw = end_data.get("date")

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


def _upsert_calendar_metadata(user_id: Optional[str], calendars: List[Dict[str, Any]]) -> None:
    if not user_id or not calendars:
        return

    conn = _get_conn()
    try:
        cur = conn.cursor()
        for cal in calendars:
            cal_id = str(cal.get("id") or "").strip()
            if not cal_id:
                continue

            cur.execute(
                """
                INSERT INTO public.google_calendars (
                    user_id, google_calendar_id, summary, description, time_zone,
                    access_role, selected, is_primary, raw_calendar, last_synced_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, google_calendar_id)
                DO UPDATE SET
                    summary = EXCLUDED.summary,
                    description = EXCLUDED.description,
                    time_zone = EXCLUDED.time_zone,
                    access_role = EXCLUDED.access_role,
                    selected = EXCLUDED.selected,
                    is_primary = EXCLUDED.is_primary,
                    raw_calendar = EXCLUDED.raw_calendar,
                    last_synced_at = EXCLUDED.last_synced_at,
                    updated_at = NOW()
                """,
                (
                    user_id,
                    cal_id,
                    cal.get("summary"),
                    cal.get("description"),
                    cal.get("time_zone"),
                    cal.get("access_role"),
                    bool(cal.get("selected", True)),
                    bool(cal.get("is_primary", cal_id == "primary")),
                    _json(cal.get("raw_calendar") or cal),
                ),
            )

        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to upsert calendar metadata snapshots: %s", exc)
    finally:
        conn.close()


def _upsert_calendar_event_snapshot(user_id: Optional[str], event: Dict) -> None:
    if not user_id:
        return

    event_id = str(event.get("id") or "").strip()
    calendar_id = str(event.get("_calendar_id") or "primary")
    if not event_id:
        return

    start_at, end_at, is_all_day, start_tz, end_tz = _event_datetime_bounds(event)
    status = str(event.get("status") or "confirmed").lower()
    readonly = event.get("_calendar_access_role") not in (None, "owner", "writer")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.google_calendar_events (
                user_id, google_calendar_id, google_event_id, ical_uid, etag,
                sequence, status, summary, description, location,
                start_at, end_at, is_all_day, start_time_zone, end_time_zone,
                html_link, meet_link, organizer, creator, attendees,
                reminders, raw_event, is_readonly, deleted_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (user_id, google_calendar_id, google_event_id)
            DO UPDATE SET
                ical_uid = EXCLUDED.ical_uid,
                etag = EXCLUDED.etag,
                sequence = EXCLUDED.sequence,
                status = EXCLUDED.status,
                summary = EXCLUDED.summary,
                description = EXCLUDED.description,
                location = EXCLUDED.location,
                start_at = EXCLUDED.start_at,
                end_at = EXCLUDED.end_at,
                is_all_day = EXCLUDED.is_all_day,
                start_time_zone = EXCLUDED.start_time_zone,
                end_time_zone = EXCLUDED.end_time_zone,
                html_link = EXCLUDED.html_link,
                meet_link = EXCLUDED.meet_link,
                organizer = EXCLUDED.organizer,
                creator = EXCLUDED.creator,
                attendees = EXCLUDED.attendees,
                reminders = EXCLUDED.reminders,
                raw_event = EXCLUDED.raw_event,
                is_readonly = EXCLUDED.is_readonly,
                deleted_at = EXCLUDED.deleted_at,
                updated_at = NOW()
            """,
            (
                user_id,
                calendar_id,
                event_id,
                event.get("iCalUID"),
                event.get("etag"),
                event.get("sequence"),
                status,
                str(event.get("summary") or "(No title)").strip() or "(No title)",
                event.get("description"),
                event.get("location"),
                start_at,
                end_at,
                is_all_day,
                start_tz,
                end_tz,
                event.get("htmlLink"),
                _extract_meet_link(event),
                _json(event.get("organizer") or {}),
                _json(event.get("creator") or {}),
                _json(event.get("attendees") or []),
                _json(event.get("reminders") or {}),
                _json(event),
                readonly,
                datetime.now(TIMEZONE) if status == "cancelled" else None,
            ),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to upsert calendar event snapshot: %s", exc)
    finally:
        conn.close()


def _mark_calendar_event_deleted(user_id: Optional[str], calendar_id: str, event_id: str) -> None:
    if not user_id:
        return

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE public.google_calendar_events
            SET status = 'cancelled', deleted_at = NOW(), updated_at = NOW()
            WHERE user_id = %s AND google_calendar_id = %s AND google_event_id = %s
            """,
            (user_id, calendar_id, event_id),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to mark calendar event deleted in snapshot table: %s", exc)
    finally:
        conn.close()


def _upsert_calendar_event_memory(user_id: Optional[str], event: Dict) -> None:
    if not user_id:
        return

    event_id = str(event.get("id") or "").strip()
    calendar_id = str(event.get("_calendar_id") or "primary")
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


def _prune_calendar_window_data(
    user_id: Optional[str],
    window_start: datetime,
    window_end: datetime,
) -> None:
    if not user_id:
        return

    stale_events: List[Tuple[str, str]] = []

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT google_calendar_id, google_event_id
            FROM public.google_calendar_events
            WHERE user_id = %s
              AND (start_at < %s OR start_at >= %s)
            """,
            (user_id, window_start, window_end),
        )
        rows = cur.fetchall() or []
        stale_events = [(str(row[0]), str(row[1])) for row in rows if len(row) >= 2]

        cur.execute(
            """
            DELETE FROM public.google_calendar_events
            WHERE user_id = %s
              AND (start_at < %s OR start_at >= %s)
            """,
            (user_id, window_start, window_end),
        )

        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("Failed to prune calendar events outside rolling window: %s", exc)
    finally:
        conn.close()

    for calendar_id, event_id in stale_events:
        external_ref = task_service.calendar_external_ref(calendar_id, event_id)
        _run_parallel_best_effort(
            lambda ext_ref=external_ref: task_service.delete_task_by_external_ref(user_id, ext_ref),
            lambda cal_id=calendar_id, evt_id=event_id: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{cal_id}:{evt_id}",
            ),
        )


def list_selected_calendars(service) -> List[Dict[str, Any]]:
    response = service.calendarList().list().execute()
    calendars: List[Dict[str, Any]] = []

    for cal in response.get("items", []):
        if not _is_supported_user_calendar(cal):
            continue

        calendars.append(
            {
                "id": cal.get("id"),
                "summary": cal.get("summary"),
                "description": cal.get("description"),
                "time_zone": cal.get("timeZone"),
                "access_role": cal.get("accessRole"),
                "selected": cal.get("selected", True),
                "is_primary": bool(cal.get("primary")),
                "raw_calendar": cal,
            }
        )

    return calendars


def _is_supported_user_calendar(cal: Dict[str, Any]) -> bool:
    is_primary = bool(cal.get("primary"))
    selected = bool(cal.get("selected", True))
    access_role = str(cal.get("accessRole") or "").strip().lower()

    calendar_id = str(cal.get("id") or "").strip().lower()
    summary = str(cal.get("summary") or "").strip().lower()

    if any(marker in calendar_id for marker in EXCLUDED_CALENDAR_ID_MARKERS):
        return False

    if any(marker in summary for marker in EXCLUDED_CALENDAR_SUMMARY_MARKERS):
        return False

    if is_primary:
        return True

    if not selected:
        return False

    return access_role in WRITABLE_CALENDAR_ACCESS_ROLES


def fetch_events_across_selected_calendars(
    service,
    time_min: str,
    time_max: str,
    selected_calendars: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict]:
    combined: List[Dict] = []

    calendars = selected_calendars or list_selected_calendars(service)
    for cal in calendars:
        cal_id = cal.get("id")
        if not cal_id:
            continue

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

        for event in result.get("items", []):
            if _is_excluded_google_special_event(event, str(cal_id), str(cal.get("summary") or "")):
                continue
            if not _is_user_related_meeting(event):
                continue
            event["_calendar_id"] = cal_id
            event["_calendar_summary"] = cal.get("summary")
            event["_calendar_access_role"] = cal.get("access_role")
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
    event_type = str(event.get("eventType") or "").strip().lower()
    if event_type == "birthday":
        return True

    organizer = event.get("organizer") if isinstance(event.get("organizer"), dict) else {}
    creator = event.get("creator") if isinstance(event.get("creator"), dict) else {}

    source_text = " ".join(
        [
            str(calendar_id or ""),
            str(calendar_summary or ""),
            str(organizer.get("email") or ""),
            str(creator.get("email") or ""),
        ]
    ).lower()

    return any(marker in source_text for marker in EXCLUDED_CALENDAR_ID_MARKERS)


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
    end_data = event.get("end", {})

    start_dt_raw = start_data.get("dateTime")
    end_dt_raw = end_data.get("dateTime")

    if start_dt_raw:
        start_dt = _to_local(_iso_to_datetime(start_dt_raw))
        event_date = start_dt.date().isoformat()
        start_time = start_dt.strftime("%H:%M")
    else:
        event_date = start_data.get("date", datetime.now(TIMEZONE).date().isoformat())
        start_time = "00:00"

    if end_dt_raw:
        end_dt = _to_local(_iso_to_datetime(end_dt_raw))
        end_time = end_dt.strftime("%H:%M")
    else:
        end_time = "23:59"

    calendar_name = event.get("_calendar_summary")
    is_readonly = event.get("_calendar_access_role") not in (None, "owner", "writer")
    event_id = event.get("id", "")
    calendar_id = event.get("_calendar_id") or "primary"
    safe_id = event_id if not is_readonly else f"{calendar_id}:{event_id}"

    description = event.get("description", "")
    if not description and calendar_name:
        description = f"From {calendar_name}"

    return {
        "id": safe_id,
        "title": event.get("summary", "(No title)"),
        "date": event_date,
        "startTime": start_time,
        "endTime": end_time,
        "description": description,
        "color": None,
        "calendarName": calendar_name,
        "readonly": is_readonly,
    }


def _calendar_event_due_date(event: Dict) -> Optional[datetime]:
    start_data = event.get("start", {})
    dt_raw = start_data.get("dateTime")
    if dt_raw:
        return _iso_to_datetime(dt_raw)

    date_raw = start_data.get("date")
    if date_raw:
        return datetime.fromisoformat(f"{date_raw}T09:00:00").replace(tzinfo=TIMEZONE)

    return None


def _sync_calendar_event_to_task(user_id: Optional[str], event: Dict) -> None:
    if not user_id:
        return

    # Use iCalUID as the unique identifier to prevent duplicates across calendars
    ical_uid = str(event.get("iCalUID") or "").strip()
    event_id = str(event.get("id") or "").strip()

    if not ical_uid and not event_id:
        return

    # Use iCalUID if available (unique across all calendars), otherwise fall back to calendar_id:event_id
    calendar_id = str(event.get("_calendar_id") or "primary")
    if ical_uid:
        external_ref = f"gcal:ical:{ical_uid}"
    else:
        external_ref = task_service.calendar_external_ref(calendar_id, event_id)

    if str(event.get("status") or "").lower() == "cancelled":
        _run_parallel_best_effort(
            lambda: task_service.delete_task_by_external_ref(user_id, external_ref),
            lambda: _mark_calendar_event_deleted(user_id, calendar_id, event_id),
            lambda: memory_service.delete_snapshot(
                user_id=user_id,
                source="calendar_event",
                external_id=f"{calendar_id}:{event_id}",
            ),
        )
        return

    summary = str(event.get("summary") or "(No title)").strip() or "(No title)"
    description = str(event.get("description") or "").strip()
    calendar_name = str(event.get("_calendar_summary") or "").strip()
    if calendar_name and not description:
        description = f"From {calendar_name}"

    due_date = _calendar_event_due_date(event)

    _run_parallel_best_effort(
        lambda: task_service.upsert_calendar_event_task(
            user_id=user_id,
            external_ref=external_ref,
            title=summary,
            description=description or None,
            due_date=due_date,
        ),
        lambda: _upsert_calendar_event_snapshot(user_id, event),
        lambda: _upsert_calendar_event_memory(user_id, event),
    )


def _sync_calendar_snapshot_to_tasks(user_id: Optional[str], events: List[Dict]) -> None:
    if not user_id:
        return

    for event in events:
        _sync_calendar_event_to_task(user_id, event)


def _delete_calendar_event_task(user_id: Optional[str], calendar_id: str, event_id: str) -> None:
    if not user_id:
        return

    # Try to get the event to find its iCalUID
    try:
        service = get_calendar_service(user_id=user_id)
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        ical_uid = str(event.get("iCalUID") or "").strip()

        if ical_uid:
            external_ref = f"gcal:ical:{ical_uid}"
        else:
            external_ref = task_service.calendar_external_ref(calendar_id, event_id)
    except Exception:
        # Fallback if we can't fetch the event
        external_ref = task_service.calendar_external_ref(calendar_id, event_id)

    _run_parallel_best_effort(
        lambda: task_service.delete_task_by_external_ref(user_id, external_ref),
        lambda: _mark_calendar_event_deleted(user_id, calendar_id, event_id),
        lambda: memory_service.delete_snapshot(
            user_id=user_id,
            source="calendar_event",
            external_id=f"{calendar_id}:{event_id}",
        ),
    )


def _build_google_event_body(payload) -> Dict:
    start_dt = force_local(datetime.strptime(f"{payload.date} {payload.startTime}", "%Y-%m-%d %H:%M"))
    end_dt = force_local(datetime.strptime(f"{payload.date} {payload.endTime}", "%Y-%m-%d %H:%M"))

    if end_dt <= start_dt:
        raise ValueError("endTime must be after startTime")

    return {
        "summary": payload.title.strip() or "(No title)",
        "description": payload.description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
    }


def get_events_for_frontend(days: int = CALENDAR_FRONTEND_WINDOW_DAYS, user_id: Optional[str] = None) -> List[Dict]:
    if days < 1:
        raise ValueError("days must be >= 1")

    window_days = min(days, CALENDAR_FRONTEND_WINDOW_DAYS)

    service = get_calendar_service(user_id=user_id)
    now = datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today_start - timedelta(days=CALENDAR_FRONTEND_LOOKBACK_DAYS)
    window_end = today_start + timedelta(days=window_days + 1)

    time_min = window_start.isoformat()
    # Include all of today plus the next N days.
    time_max = window_end.isoformat()

    selected_calendars = list_selected_calendars(service)
    _upsert_calendar_metadata(user_id, selected_calendars)

    _prune_calendar_window_data(user_id, window_start, window_end)

    events_raw = fetch_events_across_selected_calendars(
        service,
        time_min,
        time_max,
        selected_calendars=selected_calendars,
    )
    _sync_calendar_snapshot_to_tasks(user_id, events_raw)
    return [_format_event_for_frontend(event) for event in events_raw]


def create_event_from_payload(payload, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    body = _build_google_event_body(payload)
    created = service.events().insert(calendarId="primary", body=body).execute()
    created["_calendar_id"] = "primary"
    created.setdefault("_calendar_summary", "Primary")
    created.setdefault("status", "confirmed")
    _sync_calendar_event_to_task(user_id, created)
    return _format_event_for_frontend(created)


def update_event_from_payload(event_id: str, payload, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)
    body = _build_google_event_body(payload)
    updated = (
        service.events()
        .patch(calendarId=calendar_id, eventId=actual_event_id, body=body)
        .execute()
    )
    updated["_calendar_id"] = calendar_id
    updated.setdefault("_calendar_summary", "Primary")
    updated.setdefault("status", "confirmed")
    _sync_calendar_event_to_task(user_id, updated)
    return _format_event_for_frontend(updated)


def delete_event_by_id(event_id: str, user_id: Optional[str] = None) -> None:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)
    service.events().delete(calendarId=calendar_id, eventId=actual_event_id).execute()
    _delete_calendar_event_task(user_id, calendar_id, actual_event_id)


def get_events_on_date(date_str: str, user_id: Optional[str] = None) -> List[Dict]:
    service = get_calendar_service(user_id=user_id)
    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    day_start = datetime.combine(target_date, datetime.strptime("00:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)
    day_end = datetime.combine(target_date, datetime.strptime("23:59", "%H:%M").time()).replace(tzinfo=TIMEZONE)

    events = fetch_events_across_selected_calendars(service, day_start.isoformat(), day_end.isoformat())
    return [
        {
            "summary": event.get("summary", "(No title)"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "id": event.get("id"),
            "calendar": event.get("_calendar_summary", "Primary"),
        }
        for event in events
    ]


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
    service = get_calendar_service(user_id=user_id)

    parsed_dt = parse_datetime(datetime_str)
    start_dt = force_local(parsed_dt)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    start_iso = start_dt.isoformat()

    if is_duplicate_event(service, title, start_iso):
        return {
            "status": "duplicate_prevented",
            "summary": title,
            "start": start_iso,
        }

    event = {
        "summary": title,
        "start": {
            "dateTime": start_iso,
            "timeZone": TIMEZONE_NAME,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
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
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet",
                },
            }
        }

    if attendees:
        event["attendees"] = [{"email": email.strip()} for email in attendees if email and email.strip()]

    created_event = (
        service.events()
        .insert(calendarId="primary", body=event, conferenceDataVersion=1 if create_meet else 0)
        .execute()
    )

    created_event["_calendar_id"] = "primary"
    created_event.setdefault("_calendar_summary", "Primary")
    created_event.setdefault("status", "confirmed")
    _sync_calendar_event_to_task(user_id, created_event)

    meet_link = None
    conference_data = created_event.get("conferenceData")
    if conference_data:
        for entry_point in conference_data.get("entryPoints", []):
            if entry_point.get("entryPointType") == "video":
                meet_link = entry_point.get("uri")
                break

    return {
        "event_id": created_event.get("id"),
        "link": created_event.get("htmlLink"),
        "meet_link": meet_link,
        "summary": created_event.get("summary"),
        "start": created_event["start"].get("dateTime"),
        "attendees": [a.get("email") for a in created_event.get("attendees", [])],
    }


def list_upcoming_events(days: int = 1, user_id: Optional[str] = None) -> List[Dict]:
    service = get_calendar_service(user_id=user_id)

    now = datetime.now(TIMEZONE)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    events = fetch_events_across_selected_calendars(service, time_min, time_max)

    return [
        {
            "summary": event.get("summary", "(No title)"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "id": event.get("id"),
            "calendar": event.get("_calendar_summary", "Primary"),
        }
        for event in events
    ]


def list_events_in_window(
    lookback_days: int = 7,
    lookahead_days: int = 8,
    user_id: Optional[str] = None,
) -> List[Dict]:
    """List events in a window around now (past + future), excluding holidays/festivals."""
    service = get_calendar_service(user_id=user_id)

    now = datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    time_min = (today_start - timedelta(days=lookback_days)).isoformat()
    time_max = (today_start + timedelta(days=lookahead_days + 1)).isoformat()

    events = fetch_events_across_selected_calendars(service, time_min, time_max)

    return [
        {
            "summary": event.get("summary", "(No title)"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "id": event.get("id"),
            "calendar": event.get("_calendar_summary", "Primary"),
        }
        for event in events
    ]


def delete_calendar_event(event_id: str, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)
    calendar_id, actual_event_id = _parse_calendar_event_id(event_id)

    service.events().delete(calendarId=calendar_id, eventId=actual_event_id).execute()
    _delete_calendar_event_task(user_id, calendar_id, actual_event_id)
    return {
        "status": "success",
        "deleted_event_id": actual_event_id,
    }


def find_events_by_description(query: str, user_id: Optional[str] = None) -> List[Dict]:
    service = get_calendar_service(user_id=user_id)

    now = datetime.now(TIMEZONE)
    today_midnight = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=TIMEZONE)
    time_min = today_midnight.isoformat()
    time_max = (now + timedelta(days=7)).isoformat()

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
                    "start": event["start"].get("dateTime", event["start"].get("date")),
                    "id": event.get("id"),
                }
            )

    return matches


def delete_event_by_description(query: str, user_id: Optional[str] = None) -> Dict:
    matches = find_events_by_description(query, user_id=user_id)

    if not matches:
        return {
            "status": "not_found",
            "message": f"No matching event found for '{query}' in the next 7 days.",
        }

    if len(matches) == 1:
        event = matches[0]
        service = get_calendar_service(user_id=user_id)
        service.events().delete(calendarId="primary", eventId=event["id"]).execute()
        _delete_calendar_event_task(user_id, "primary", event["id"])

        return {
            "status": "deleted",
            "deleted_summary": event["summary"],
            "deleted_start": event["start"],
            "deleted_id": event["id"],
        }

    return {
        "status": "multiple_matches",
        "message": f"Found {len(matches)} events matching '{query}'. Please specify which one:",
        "matches": [{"summary": m["summary"], "start": m["start"], "id": m["id"]} for m in matches],
    }


def modify_event_by_description(query: str, new_datetime_str: str, user_id: Optional[str] = None) -> Dict:
    matches = find_events_by_description(query, user_id=user_id)

    if not matches:
        return {
            "status": "not_found",
            "message": f"No matching event found for '{query}' in the next 7 days.",
        }

    if len(matches) > 1:
        return {
            "status": "multiple_matches",
            "message": f"Found {len(matches)} events matching '{query}'. Please specify which one:",
            "matches": [{"summary": m["summary"], "start": m["start"], "id": m["id"]} for m in matches],
        }

    event_match = matches[0]
    service = get_calendar_service(user_id=user_id)

    full_event = service.events().get(calendarId="primary", eventId=event_match["id"]).execute()

    old_start_str = full_event["start"].get("dateTime")
    old_end_str = full_event["end"].get("dateTime")

    if old_start_str and old_end_str:
        old_start = _iso_to_datetime(old_start_str)
        old_end = _iso_to_datetime(old_end_str)
        original_duration = old_end - old_start
    else:
        original_duration = timedelta(minutes=60)

    new_start = force_local(parse_datetime(new_datetime_str))
    new_end = new_start + original_duration

    patch_body = {
        "start": {
            "dateTime": new_start.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
        "end": {
            "dateTime": new_end.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
    }

    updated_event = (
        service.events()
        .patch(calendarId="primary", eventId=event_match["id"], body=patch_body)
        .execute()
    )

    updated_event["_calendar_id"] = "primary"
    updated_event.setdefault("_calendar_summary", "Primary")
    updated_event.setdefault("status", "confirmed")
    _sync_calendar_event_to_task(user_id, updated_event)

    return {
        "status": "modified",
        "summary": updated_event.get("summary"),
        "old_start": old_start_str,
        "new_start": updated_event["start"].get("dateTime"),
        "new_end": updated_event["end"].get("dateTime"),
        "duration_minutes": int(original_duration.total_seconds() / 60),
        "link": updated_event.get("htmlLink"),
    }


def find_free_slots(date_str: str, duration_minutes: int = 30, user_id: Optional[str] = None) -> Dict:
    service = get_calendar_service(user_id=user_id)

    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    day_start = datetime.combine(target_date, datetime.strptime("08:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)
    day_end = datetime.combine(target_date, datetime.strptime("22:00", "%H:%M").time()).replace(tzinfo=TIMEZONE)

    events = fetch_events_across_selected_calendars(service, day_start.isoformat(), day_end.isoformat())

    busy = []
    for event in events:
        start_str = event["start"].get("dateTime")
        end_str = event["end"].get("dateTime")
        if start_str and end_str:
            busy.append((_iso_to_datetime(start_str), _iso_to_datetime(end_str)))

    busy.sort(key=lambda x: x[0])

    free_slots = []
    cursor = day_start

    for busy_start, busy_end in busy:
        busy_start = max(busy_start, day_start)
        busy_end = min(busy_end, day_end)

        if cursor < busy_start:
            gap_minutes = int((busy_start - cursor).total_seconds() / 60)
            if gap_minutes >= duration_minutes:
                free_slots.append(
                    {
                        "start": cursor.strftime("%H:%M"),
                        "end": busy_start.strftime("%H:%M"),
                        "duration_minutes": gap_minutes,
                    }
                )

        cursor = max(cursor, busy_end)

    if cursor < day_end:
        gap_minutes = int((day_end - cursor).total_seconds() / 60)
        if gap_minutes >= duration_minutes:
            free_slots.append(
                {
                    "start": cursor.strftime("%H:%M"),
                    "end": day_end.strftime("%H:%M"),
                    "duration_minutes": gap_minutes,
                }
            )

    return {
        "date": date_str,
        "requested_duration": duration_minutes,
        "free_slots": free_slots,
        "total_free_slots": len(free_slots),
    }
