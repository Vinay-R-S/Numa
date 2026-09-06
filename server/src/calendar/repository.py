"""Calendar persistence layer: cal_calendars / cal_events / cal_attendees SQL
plus Qdrant/task/memory cleanup (NUMA-104 P3, PLAN 16.1).

All DB access for the calendar feature lives here. Extracted verbatim from
calendar/service.py; service.py re-exports these names.

Note: _persist_mutated_event lives here (not in google_client as sketched in
PLAN 16.1) because it orchestrates _ensure_cal_calendar / _store_cal_event;
keeping it here avoids a repository <-> google_client import cycle.
"""
import os
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from ..db import _get_conn
from ..memory import memory_service
from ..memory.service import (
    store_calendar_event as _qdrant_store_event,
    delete_month_calendar_events as _qdrant_delete_month,
    delete_calendar_event as _qdrant_delete_event,
)
from ..tasks import service as task_service
from .datetime_utils import TIMEZONE, _to_local, _event_datetime_bounds
from .calendars import (
    _color_for_calendar_type,
    _primary_calendar_entry,
    _primary_calendar_ids,
)
from .google_auth import get_calendar_service, _get_user_email
from .google_client import _extract_meet_link, _run_parallel_best_effort

log = logging.getLogger(__name__)

# How long to consider the DB cache fresh before re-fetching from Google
CACHE_TTL_MINUTES = int(os.getenv("CALENDAR_CACHE_TTL_MINUTES", "30"))

# Last etag embedded per event, so the 30-minute sync stops paying for an
# embedding of text that has not changed. The scheduler replays every event of
# every connected user on every tick, and each one used to be re-embedded
# synchronously (NUMA-142 P6, PLAN 9). Google changes the etag whenever the
# event changes, so an unchanged etag means the stored vector is still correct.
# Process-local and bounded: after a restart each event is embedded once more.
_INGESTED_ETAG_MAX = 20000
_ingested_etags: "OrderedDict[str, str]" = OrderedDict()
_ingested_lock = threading.Lock()


def _already_ingested(user_id: str, google_event_id: str, etag: str) -> bool:
    if not etag or not google_event_id:
        return False
    key = f"{user_id}:{google_event_id}"
    with _ingested_lock:
        if _ingested_etags.get(key) == etag:
            _ingested_etags.move_to_end(key)
            return True
        return False


def _forget_ingested(user_id: str, google_event_id: str) -> None:
    """Drop the memo for an event whose vector was just deleted.

    Without this a re-created or restored event with an unchanged etag would
    never be re-embedded for the life of the process (NUMA-142 P6 review).
    """
    if not google_event_id:
        return
    with _ingested_lock:
        _ingested_etags.pop(f"{user_id}:{google_event_id}", None)


def _forget_all_ingested(user_id: str) -> None:
    """Drop every memo for one user, after a bulk vector delete."""
    prefix = f"{user_id}:"
    with _ingested_lock:
        for key in [k for k in _ingested_etags if k.startswith(prefix)]:
            _ingested_etags.pop(key, None)


def _mark_ingested(user_id: str, google_event_id: str, etag: str) -> None:
    if not etag or not google_event_id:
        return
    key = f"{user_id}:{google_event_id}"
    with _ingested_lock:
        _ingested_etags[key] = etag
        _ingested_etags.move_to_end(key)
        while len(_ingested_etags) > _INGESTED_ETAG_MAX:
            _ingested_etags.popitem(last=False)


# CACHE LAYER - read from cal_events DB before hitting Google API

def _is_cache_fresh_for_month(user_id: str, month_start: datetime, month_end: datetime) -> bool:
    """
    Return True if:
    1. At least one cal_calendar exists for this user, AND
    2. The most recently synced calendar was synced within CACHE_TTL_MINUTES, AND
    3. There is at least one cal_event within the current month window.

    This avoids hitting the Google API on every page load.
    """
    conn = None
    try:
        conn = _get_conn()
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
        if conn is not None:
            conn.close()


def _read_month_events_from_db(user_id: str, month_start: datetime, month_end: datetime) -> List[Dict]:
    """
    Read all active cal_events for the current month from the DB and format
    them for the frontend. No Google API call needed.

    This is the Groq-token-saving path: the agent can also call SQL against
    cal_events instead of re-fetching JSON from Google.
    """
    conn = None
    try:
        conn = _get_conn()
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
                c.access_role   AS access_role,
                c.is_primary    AS is_primary
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
            # The same rule as `_format_event_for_frontend`, and for the same
            # reason: `_parse_calendar_event_id` reads a bare id as belonging to
            # "primary", so an event on a secondary calendar the user owns
            # (access role "owner", therefore not readonly) had its update and
            # delete routed to the wrong calendar and answered 404. This path
            # serves every load for CALENDAR_CACHE_TTL_MINUTES after a refresh,
            # so keying it on `is_readonly` while the Google path keyed on
            # `is_primary` also gave one event two different ids depending on
            # which path served it (NUMA-142 P6 review).
            is_primary = bool(r.get("is_primary")) or google_cal_id == "primary"
            safe_id = google_event_id if is_primary else f"{google_cal_id}:{google_event_id}"

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
        if conn is not None:
            conn.close()


# NORMALIZED STORAGE - cal_calendars / cal_events / cal_attendees

# Slim agent-facing read. One literal statement over a half-open window, so the
# repository keeps zero f-string SQL (PLAN 8) and callers share one bound rule.
_AGENT_EVENTS_SQL = """
    SELECT e.google_event_id, e.title, e.start_at, c.name
    FROM public.cal_events e
    JOIN public.cal_calendars c ON c.id = e.calendar_id
    WHERE e.user_id     = %s
      AND e.start_at   >= %s
      AND e.start_at   <  %s
      AND e.deleted_at IS NULL
      AND c.calendar_type IN ('personal', 'shared')
    ORDER BY e.start_at
"""


def read_events_between(user_id: str, window_start: datetime, window_end: datetime) -> List[Dict]:
    """
    Slim agent-facing read of personal/shared events in the half-open window
    [window_start, window_end) - holidays and birthdays excluded.

    Returns [] when nothing is cached OR the read fails (including a failure to
    acquire a connection), so callers fall back to the Google API.
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(_AGENT_EVENTS_SQL, (user_id, window_start, window_end))
        rows = cur.fetchall() or []
        cur.close()
        return [
            {
                "summary": row[1],
                "start": _to_local(row[2]).isoformat(),
                "id": row[0],
                "calendar": row[3],
            }
            for row in rows
        ]
    except Exception as exc:
        log.warning("Failed to read cached calendar events: %s", exc)
        return []
    finally:
        if conn is not None:
            conn.close()


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

    conn = None
    try:
        conn = _get_conn()
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
        if conn is not None:
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

    conn = None
    try:
        conn = _get_conn()
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
        if conn is not None:
            conn.close()


def _upsert_cal_attendees(event_uuid: str, attendees_raw: Any) -> None:
    """
    Parse attendees list from a Google event and upsert into cal_attendees.
    One row per attendee - no JSON blobs - so the agent can query RSVP status
    with plain SQL instead of re-fetching from Google.
    """
    if not isinstance(attendees_raw, list) or not attendees_raw:
        return

    conn = None
    try:
        conn = _get_conn()
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
        if conn is not None:
            conn.close()


def _store_cal_event(user_id: str, calendar_uuid: str, event: Dict) -> None:
    """Persist one Google event dict to the normalized cal_events + cal_attendees tables,
    then ingest its embedding into the Qdrant calendar collection."""
    event_uuid = _upsert_cal_event(user_id, calendar_uuid, event)
    if not event_uuid:
        return
    _upsert_cal_attendees(event_uuid, event.get("attendees") or [])

    # Qdrant ingest (best-effort, non-blocking)
    try:
        google_event_id = str(event.get("id")             or "").strip()
        google_cal_id   = str(event.get("_calendar_id")   or "primary")
        cal_type        = str(event.get("_calendar_type") or "personal")
        title           = str(event.get("summary")        or "(No title)").strip()
        description     = event.get("description")
        start_at, end_at, is_all_day, _, _ = _event_datetime_bounds(event)
        etag = str(event.get("etag") or "")

        if not google_event_id or _already_ingested(user_id, google_event_id, etag):
            return

        # Resolve the user's Google email from the token file (cached per user)
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
            _mark_ingested(user_id, google_event_id, etag)
    except Exception as exc:
        log.warning("Qdrant ingest failed for event (non-fatal): %s", exc)


def _known_calendar(user_id: str, google_cal_id: str) -> Optional[Dict]:
    """The calendar as we already synced it, or None if we have never seen it.

    `_ensure_cal_calendar` overwrites name, access_role, is_primary and
    calendar_type on every upsert, so any field a caller guesses at is written
    over the truth. A calendar the full sync already classified is the
    authoritative answer and costs one indexed read, rather than a Google round
    trip on every event edit.
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT name, access_role, is_primary, calendar_type "
            "FROM public.cal_calendars WHERE user_id = %s AND google_cal_id = %s",
            (user_id, google_cal_id),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": google_cal_id,
            "summary": row[0],
            "access_role": row[1],
            "is_primary": row[2],
            "calendar_type": row[3],
        }
    except Exception:
        log.debug("Could not read the stored calendar %s", google_cal_id, exc_info=True)
        return None
    finally:
        if conn is not None:
            conn.close()


def _persist_mutated_event(user_id: Optional[str], service, event: Dict) -> None:
    if not user_id:
        return

    google_cal_id = str(event.get("_calendar_id") or "primary")
    if google_cal_id == "primary":
        cal = _primary_calendar_entry(service)
    else:
        # The stored row first. Editing one event on a shared calendar used to
        # rewrite that calendar's name to "Primary", its type to personal and
        # its access role to owner, because the caller supplied those as
        # defaults and the upsert overwrites every column. Every event on the
        # calendar then rendered with the wrong name and colour and an
        # unprefixed id, which also made them un-addressable for update and
        # delete (NUMA-142 P6, PLAN 7).
        cal = _known_calendar(user_id, google_cal_id) or {
            # Only for a calendar no sync has ever classified. Guessing is still
            # wrong here, but there is no stored truth to prefer, and the next
            # full refresh reclassifies it.
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


def _prune_cal_events_outside_month(
    user_id: str,
    month_start: datetime,
    month_end:   datetime,
) -> None:
    """
    Delete cal_events (and cascaded attendees) outside the current month window,
    then clean up linked tasks, memory snapshots, and Qdrant calendar vectors.
    """
    conn = None
    stale: List[Tuple[str, str, str]] = []
    try:
        conn = _get_conn()
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
        if conn is not None:
            conn.close()

    for _evt_uuid, cal_id, event_id in stale:
        ext_ref = task_service.calendar_external_ref(cal_id, event_id)
        _forget_ingested(user_id, event_id)
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
        # The whole month's vectors are gone, so no memo for this user is safe
        # to trust any more (NUMA-142 P6 review).
        _forget_all_ingested(user_id)
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
    conn = None
    try:
        conn = _get_conn()
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
        # `conn` is None when the failure was acquiring it, which is exactly the
        # pool-exhaustion case this handler exists to absorb (NUMA-142 P6 review).
        if conn is not None:
            conn.rollback()
    finally:
        if conn is not None:
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
            lambda e=event_id: _forget_ingested(user_id, e),
        )


def _delete_cal_event_cleanup(
    user_id: Optional[str],
    google_cal_id: str,
    google_event_id: str,
    service=None,
) -> None:
    """Soft-delete in cal_events and clean up tasks + memory.

    `service` is the caller's Google client. Every caller already has one, and
    building a second here was the last place the injected
    `CalendarService._service_factory` did not reach: a test that swapped the
    factory still had this path call the real Google API (NUMA-143 P7, PLAN 5.2).
    """
    if not user_id:
        return

    ical_uid: Optional[str] = None
    resolved_calendar_ids = [google_cal_id]
    try:
        if service is None:
            service = get_calendar_service(user_id=user_id)
        # Both directions. The primary calendar answers to the alias "primary"
        # and to the user's email address, and a ref written under one must
        # still be found when the delete arrives under the other
        # (NUMA-142 P6 review).
        primary_ids = _primary_calendar_ids(service)
        if google_cal_id in primary_ids:
            resolved_calendar_ids = primary_ids
        event    = service.events().get(calendarId=google_cal_id, eventId=google_event_id).execute()
        ical_uid = str(event.get("iCalUID") or "").strip() or None
    except Exception:
        # Best-effort: without the iCalUID the cleanup falls back to the
        # google_event_id, which is why this does not raise.
        log.debug("Could not resolve iCalUID for %s", google_event_id, exc_info=True)

    resolved_calendar_ids = list(dict.fromkeys([cid for cid in resolved_calendar_ids if cid]))

    external_ref = (
        f"gcal:ical:{ical_uid}"
        if ical_uid
        else task_service.calendar_external_ref(google_cal_id, google_event_id)
    )
    external_refs = {external_ref}
    for cal_id in resolved_calendar_ids:
        external_refs.add(task_service.calendar_external_ref(cal_id, google_event_id))

    conn = None
    try:
        conn = _get_conn()
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
        if conn is not None:
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
        lambda: _forget_ingested(user_id, google_event_id),
    )
