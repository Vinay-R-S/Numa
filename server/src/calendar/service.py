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

Module layout (NUMA-104 P3, PLAN 16.1)
--------------------------------------
This file is now a thin orchestration + public facade. The implementation lives
in cohesive sibling modules, re-exported here so existing callers are unaffected:

  datetime_utils  - timezone + datetime parsing helpers
  google_auth     - OAuth, credentials, token-path helpers
  calendars       - calendar classification + list helpers
  google_client   - Google API fetch/format/build helpers
  repository      - cal_* SQL + task/memory/Qdrant persistence
  sync            - calendar -> task/memory sync
  agent.tools     - agent-facing create/modify/delete/find tools

Orchestration class (NUMA-114 P4, PLAN 16.1 / 21.1)
---------------------------------------------------
The six entrypoints now live on `CalendarService`, with the repository, the
task/memory sync and the Google service factory injected through the
constructor. The module-level functions are thin delegating shims over the
`calendar_service` singleton, so every existing import path is unchanged. The
last two raw SQL blocks moved into `repository.read_events_between`, so the
service no longer touches the DB pool (PLAN 18).
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..core.base import BaseService
from . import repository as calendar_repository
from . import sync as calendar_sync
from .datetime_utils import (
    TIMEZONE_NAME,
    TIMEZONE,
    DATETIME_FORMATS,
    _resolve_timezone,
    parse_datetime,
    force_local,
    _to_local,
    _iso_to_datetime,
    _event_datetime_bounds,
    _current_month_window,
)
from .google_auth import (
    GOOGLE_SCOPES,
    _require_google_calendar_deps,
    _candidate_credentials_paths,
    _resolve_credentials_file,
    _legacy_token_file,
    _token_dir,
    _user_token_file,
    _load_client_config,
    has_calendar_credentials,
    _token_missing_required_scopes,
    build_google_oauth_authorization_url,
    exchange_google_oauth_code,
    get_credentials,
    _get_user_email,
    get_all_connected_user_ids,
    get_calendar_service,
)
from .calendars import (
    WRITABLE_CALENDAR_ACCESS_ROLES,
    CONTACTS_CALENDAR_MARKER,
    HOLIDAY_CALENDAR_MARKER,
    BIRTHDAY_SUMMARY_KEYWORDS,
    _CALENDAR_TYPE_COLORS,
    _get_calendar_type,
    _color_for_calendar_type,
    _primary_calendar_entry,
    _primary_calendar_ids,
    list_all_calendars,
    list_selected_calendars,
    _is_supported_user_calendar,
)
from .google_client import (
    SYNC_WORKERS,
    _parse_calendar_event_id,
    _run_parallel_best_effort,
    _extract_meet_link,
    fetch_events_across_selected_calendars,
    _is_excluded_google_special_event,
    _is_user_related_meeting,
    _format_event_for_frontend,
    _build_google_event_body,
)
from .repository import (
    CACHE_TTL_MINUTES,
    read_events_between,
    _is_cache_fresh_for_month,
    _read_month_events_from_db,
    _ensure_cal_calendar,
    _upsert_cal_event,
    _upsert_cal_attendees,
    _store_cal_event,
    _persist_mutated_event,
    _prune_cal_events_outside_month,
    _reconcile_deleted_events_for_month,
    _delete_cal_event_cleanup,
)
from .sync import (
    _upsert_calendar_event_memory,
    _calendar_event_due_date,
    _sync_calendar_event_to_task,
    _sync_all_events_to_tasks,
)
from .agent.tools import (
    is_duplicate_event,
    create_calendar_event,
    delete_calendar_event,
    find_events_by_description,
    delete_event_by_description,
    modify_event_by_description,
    find_free_slots,
)

log = logging.getLogger(__name__)


class CalendarService(BaseService):
    """
    Calendar orchestration (PLAN 16.1 / 21.1).

    Owns the month fetch + cache decision, the agent-facing reads and the
    create/update/delete flows. Collaborators are injected: the repository for
    persistence, the sync module for the task/memory mirror, and the Google
    service factory. Pure helpers (datetime maths, calendar classification,
    payload formatting) stay plain module functions.
    """

    def __init__(
        self,
        repository=calendar_repository,
        sync=calendar_sync,
        service_factory: Callable = get_calendar_service,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._sync = sync
        self._service_factory = service_factory

    # ── Main frontend fetch (with cache) ─────────────────────────────────────

    def get_events_for_frontend(
        self,
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

        # ── Try DB cache first ───────────────────────────────────────────────
        if user_id and not force_refresh:
            if self._repository._is_cache_fresh_for_month(user_id, month_start, month_end):
                cached = self._repository._read_month_events_from_db(user_id, month_start, month_end)
                if cached:
                    self.log.debug("Serving calendar from DB cache for user %s", user_id)
                    return cached

        # ── Full Google API fetch ────────────────────────────────────────────
        service = self._service_factory(user_id=user_id)

        # Include ALL calendars (holidays, birthdays, personal)
        all_calendars = list_all_calendars(service)

        time_min = month_start.isoformat()
        time_max = month_end.isoformat()

        # Build UUID map: google_cal_id -> (cal_uuid, cal_type)
        cal_uuid_map: Dict[str, Tuple[str, str]] = {}
        if user_id:
            for cal in all_calendars:
                try:
                    cal_type = cal.get("calendar_type") or "personal"
                    cal_uuid = self._repository._ensure_cal_calendar(user_id, cal, calendar_type=cal_type)
                    cal_uuid_map[str(cal.get("id") or "")] = (cal_uuid, cal_type)
                except Exception as exc:
                    self.log.warning("Could not upsert cal_calendar: %s", exc)

        # Prune events outside the current month
        if user_id:
            self._repository._prune_cal_events_outside_month(user_id, month_start, month_end)

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
                    self._repository._store_cal_event(user_id, cal_uuid, event)
                self._sync._sync_calendar_event_to_task(user_id, event)
            self._repository._reconcile_deleted_events_for_month(
                user_id,
                month_start,
                month_end,
                fetched_calendar_ids,
                active_events,
            )

        return [_format_event_for_frontend(event) for event in events_raw]


    # ── Agent-facing fetches (no cache, no holidays, lean format) ────────────

    def _fetch_agent_events_from_google(
        self,
        user_id: Optional[str],
        time_min: str,
        time_max: str,
    ) -> List[Dict]:
        service = self._service_factory(user_id=user_id)
        events = fetch_events_across_selected_calendars(
            service,
            time_min,
            time_max,
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

    def get_events_on_date(self, date_str: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Return a slim list of events on a specific date.
        Reads from DB first (Groq-token-friendly); falls back to Google API.

        A malformed date raises ValueError from `_day_bounds`.
        """
        day_start, day_end = _day_bounds(date_str)

        if user_id:
            cached = self._repository.read_events_between(user_id, day_start, day_end)
            if cached:
                return cached

        return self._fetch_agent_events_from_google(
            user_id, day_start.isoformat(), day_end.isoformat()
        )

    def list_events_in_window(
        self,
        lookback_days: int = 7,
        lookahead_days: int = 8,
        user_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        List personal events in a window around now.
        Reads from DB when possible; falls back to Google API.
        Used by the AI agent tools (holidays excluded).
        """
        today_start = datetime.now(TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = today_start - timedelta(days=lookback_days)
        window_end   = today_start + timedelta(days=lookahead_days + 1)

        # Only when the whole window is inside the month the cache actually
        # holds. `_prune_cal_events_outside_month` hard-deletes every row
        # outside the current month, so on the 2nd a non-empty result for the
        # 1st-2nd satisfied `if cached:` and the agent answered "no meetings
        # last week" for a week that was full of them (NUMA-142 P6, PLAN 7).
        month_start, month_end = _current_month_window()
        window_cached = month_start <= window_start and window_end <= month_end

        # Deliberately all-or-nothing. Clamping the window to the month and
        # asking Google only for the remainder looks like it would keep the
        # cache working near a month boundary, but the Google fallback costs one
        # round trip per selected calendar whatever the window width, so the
        # remainder call happens either way and nothing is saved; merging the
        # two result sets would add dedup and ordering risk on an agent read
        # path for no fewer API calls. The real fix is to stop pruning
        # cal_events to a single month (NUMA-142 P6 review).

        if user_id and window_cached:
            cached = self._repository.read_events_between(user_id, window_start, window_end)
            if cached:
                return cached

        return self._fetch_agent_events_from_google(
            user_id, window_start.isoformat(), window_end.isoformat()
        )

    # ── Event mutations (create / update / delete) ───────────────────────────

    def create_event_from_payload(self, payload, user_id: Optional[str] = None) -> Dict:
        service = self._service_factory(user_id=user_id)
        body    = _build_google_event_body(payload)
        created = service.events().insert(calendarId="primary", body=body).execute()
        created["_calendar_id"]   = "primary"
        created["_calendar_type"] = "personal"
        created.setdefault("_calendar_summary", "Primary")
        created.setdefault("status", "confirmed")
        self._repository._persist_mutated_event(user_id, service, created)
        self._sync._sync_calendar_event_to_task(user_id, created)
        return _format_event_for_frontend(created)

    def update_event_from_payload(self, event_id: str, payload, user_id: Optional[str] = None) -> Dict:
        service = self._service_factory(user_id=user_id)
        calendar_id, actual_event_id = _parse_calendar_event_id(event_id)
        body    = _build_google_event_body(payload)
        updated = (
            service.events()
            .patch(calendarId=calendar_id, eventId=actual_event_id, body=body)
            .execute()
        )
        updated["_calendar_id"] = calendar_id
        # Neither the type nor the summary is asserted here any more. This route
        # knows which calendar the event is on and nothing else about it, and
        # the two values it used to invent were written straight over the real
        # cal_calendars row (NUMA-142 P6). _persist_mutated_event resolves them
        # from the calendar we already synced.
        updated.setdefault("status", "confirmed")
        self._repository._persist_mutated_event(user_id, service, updated)
        self._sync._sync_calendar_event_to_task(user_id, updated)
        return _format_event_for_frontend(updated)

    def delete_event_by_id(self, event_id: str, user_id: Optional[str] = None) -> None:
        service = self._service_factory(user_id=user_id)
        calendar_id, actual_event_id = _parse_calendar_event_id(event_id)

        try:
            service.events().delete(calendarId=calendar_id, eventId=actual_event_id).execute()
        except Exception as exc:
            # HTTP 410 Gone means the event was already deleted on Google's side.
            # Treat as success and proceed with local DB / task / Qdrant cleanup.
            err_str = str(exc)
            if "410" in err_str or "Resource has been deleted" in err_str:
                self.log.info(
                    "Event %s/%s already deleted on Google (410) - proceeding with local cleanup.",
                    calendar_id, actual_event_id,
                )
            else:
                raise  # Re-raise unexpected errors

        # Always clean up PostgreSQL, tasks, and Qdrant regardless of Google's response.
        # The injected service is passed through, so a test that swaps the
        # factory no longer reaches the real Google API here (NUMA-143 P7).
        self._repository._delete_cal_event_cleanup(
            user_id, calendar_id, actual_event_id, service=service,
        )


def _day_bounds(date_str: str) -> Tuple[datetime, datetime]:
    """
    Half-open local-timezone day window [midnight, next midnight), shared by the
    cached read and the Google fallback so both cover the same instants.

    Raises ValueError on a malformed date, as the Google path always did.
    """
    target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=TIMEZONE)
    return day_start, day_start + timedelta(days=1)


calendar_service = CalendarService()


# ── Module-level shims: keep every existing import path working ───────────────

def get_events_for_frontend(user_id: Optional[str] = None, force_refresh: bool = False) -> List[Dict]:
    return calendar_service.get_events_for_frontend(user_id=user_id, force_refresh=force_refresh)


def get_events_on_date(date_str: str, user_id: Optional[str] = None) -> List[Dict]:
    return calendar_service.get_events_on_date(date_str, user_id=user_id)


def list_events_in_window(
    lookback_days: int = 7,
    lookahead_days: int = 8,
    user_id: Optional[str] = None,
) -> List[Dict]:
    return calendar_service.list_events_in_window(
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
        user_id=user_id,
    )


def create_event_from_payload(payload, user_id: Optional[str] = None) -> Dict:
    return calendar_service.create_event_from_payload(payload, user_id=user_id)


def update_event_from_payload(event_id: str, payload, user_id: Optional[str] = None) -> Dict:
    return calendar_service.update_event_from_payload(event_id, payload, user_id=user_id)


def delete_event_by_id(event_id: str, user_id: Optional[str] = None) -> None:
    calendar_service.delete_event_by_id(event_id, user_id=user_id)


# Public facade: names re-exported from the sibling modules above so existing
# import paths (``from ..calendar.service import X``) keep working unchanged.
__all__ = [
    # datetime_utils
    "TIMEZONE_NAME", "TIMEZONE", "DATETIME_FORMATS", "_resolve_timezone",
    "parse_datetime", "force_local", "_to_local", "_iso_to_datetime",
    "_event_datetime_bounds", "_current_month_window",
    # google_auth
    "GOOGLE_SCOPES", "_require_google_calendar_deps", "_candidate_credentials_paths",
    "_resolve_credentials_file", "_legacy_token_file", "_token_dir",
    "_user_token_file", "_load_client_config", "has_calendar_credentials",
    "_token_missing_required_scopes", "build_google_oauth_authorization_url",
    "exchange_google_oauth_code", "get_credentials", "_get_user_email",
    "get_all_connected_user_ids", "get_calendar_service",
    # calendars
    "WRITABLE_CALENDAR_ACCESS_ROLES", "CONTACTS_CALENDAR_MARKER",
    "HOLIDAY_CALENDAR_MARKER", "BIRTHDAY_SUMMARY_KEYWORDS", "_CALENDAR_TYPE_COLORS",
    "_get_calendar_type", "_color_for_calendar_type", "_primary_calendar_entry",
    "_primary_calendar_ids", "list_all_calendars", "list_selected_calendars",
    "_is_supported_user_calendar",
    # google_client
    "SYNC_WORKERS", "_parse_calendar_event_id", "_run_parallel_best_effort",
    "_extract_meet_link", "fetch_events_across_selected_calendars",
    "_is_excluded_google_special_event", "_is_user_related_meeting",
    "_format_event_for_frontend", "_build_google_event_body",
    # repository
    "CACHE_TTL_MINUTES", "read_events_between",
    "_is_cache_fresh_for_month", "_read_month_events_from_db",
    "_ensure_cal_calendar", "_upsert_cal_event", "_upsert_cal_attendees",
    "_store_cal_event", "_persist_mutated_event", "_prune_cal_events_outside_month",
    "_reconcile_deleted_events_for_month", "_delete_cal_event_cleanup",
    # sync
    "_upsert_calendar_event_memory", "_calendar_event_due_date",
    "_sync_calendar_event_to_task", "_sync_all_events_to_tasks",
    # agent tools
    "is_duplicate_event", "create_calendar_event", "delete_calendar_event",
    "find_events_by_description", "delete_event_by_description",
    "modify_event_by_description", "find_free_slots",
    # local orchestration (class + singleton + shims)
    "CalendarService", "calendar_service",
    "get_events_for_frontend", "get_events_on_date", "list_events_in_window",
    "create_event_from_payload", "update_event_from_payload", "delete_event_by_id",
]
