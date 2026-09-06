"""One definition of the user's timezone, and therefore of "today".

Five modules each meant something different by "today": the Slack due-date
parser built it in UTC, `github_agent.persistence` counted commits from UTC
midnight, `master_agent.orchestrator` stamped a server-local date with a UTC
tzinfo, `dashboard.service` mixed a server-local date with the database
session's `DATE()`, and only `health_agent` read the user's profile at all. On a
UTC host an IST user is a day ahead from 18:30 UTC, so each of those disagreed
with the others for five and a half hours a day (NUMA-142 P6, PLAN 7).

This is the shared mechanism: the user's own zone from `public.profiles`, the
`TIMEZONE` environment default when they have none, and UTC when even that is
unusable. Every failure resolves to a zone rather than raising - a bad profile
value is a wrong day, not a dead request.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")

# Profiles change rarely and this is read on hot paths (every dashboard load,
# every sync tick, every agent turn), so the lookup is cached briefly.
_CACHE_TTL_SECONDS = 300
_CACHE_MAX = 512
_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()


def default_timezone_name() -> str:
    return (os.getenv("TIMEZONE") or "Asia/Kolkata").strip() or "Asia/Kolkata"


def resolve_timezone(name: Optional[str]) -> ZoneInfo:
    """Return the named zone, the configured default, or UTC.

    Catches every exception, not just `ZoneInfoNotFoundError`: a value like
    "GMT+5:30" or an empty tzdata install raises `ValueError` instead, which
    used to escape the fallback that exists to prevent exactly that.
    """
    for candidate in (name, default_timezone_name(), "UTC"):
        if not candidate or not str(candidate).strip():
            continue
        try:
            return ZoneInfo(str(candidate).strip())
        except Exception:
            log.debug("Unusable timezone %r; trying the next candidate", candidate)
    return _UTC


def _cached_name(user_id: str) -> Optional[str]:
    with _cache_lock:
        entry = _cache.get(user_id)
        if not entry:
            return None
        if time.time() - entry[0] >= _CACHE_TTL_SECONDS:
            _cache.pop(user_id, None)
            return None
        return entry[1]


def _remember(user_id: str, name: str) -> None:
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[user_id] = (time.time(), name)


def _profile_timezone_name(user_id: str) -> Optional[str]:
    from .db import get_db

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT timezone FROM public.profiles WHERE id = %s LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        return (row[0] or "").strip() if row and row[0] else None


def user_timezone(user_id: Optional[str]) -> ZoneInfo:
    """The user's own zone, falling back to the configured default."""
    uid = (user_id or "").strip()
    if not uid:
        return resolve_timezone(None)

    cached = _cached_name(uid)
    if cached:
        return resolve_timezone(cached)

    try:
        name = _profile_timezone_name(uid)
    except Exception as exc:
        log.debug("Could not read the profile timezone for %s: %s", uid, exc)
        return resolve_timezone(None)

    resolved = resolve_timezone(name)
    _remember(uid, name or default_timezone_name())
    return resolved


def user_now(user_id: Optional[str]) -> datetime:
    """Now, in the user's zone. Aware, always."""
    return datetime.now(user_timezone(user_id))


def user_today(user_id: Optional[str]) -> date:
    """The calendar date it is where the user is, not where the server is."""
    return user_now(user_id).date()


def forget_user(user_id: str) -> None:
    """Drop a cached zone, for when a profile's timezone is updated."""
    with _cache_lock:
        _cache.pop(user_id, None)
