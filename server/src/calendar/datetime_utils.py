"""Calendar datetime and timezone helpers (NUMA-104 P3, PLAN 16.1).

Leaf module: stdlib only, no calendar/DB imports. Extracted verbatim from
calendar/service.py; service.py re-exports these names so callers are unaffected.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from ..core.timezones import default_timezone_name, resolve_timezone

log = logging.getLogger(__name__)

# `default_timezone_name`, not a bare `os.getenv("TIMEZONE", ...)`: a
# set-but-empty variable (a commented-out value, or a platform that injects an
# empty var) returned "" rather than the default.
TIMEZONE_NAME = default_timezone_name()


def _resolve_timezone() -> ZoneInfo:
    """The configured zone, via the shared resolver.

    This caught only `ZoneInfoNotFoundError`, but an empty or malformed name
    raises `ValueError` instead - and this module is on the boot path
    (`main.py` -> calendar router -> service -> here), so the app died at import
    with an unhandled ValueError rather than falling back (NUMA-142 P6 review).
    """
    return resolve_timezone(TIMEZONE_NAME)


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


def parse_datetime(datetime_str: str) -> datetime:
    # The trailing `Z` used to be deleted here, which turned a UTC instant into
    # a naive wall clock before anything downstream could see it was UTC. On
    # 3.11 `fromisoformat` understands `Z`, so it is tried first with the string
    # intact and only stripped for the older `strptime` formats, which cannot
    # (NUMA-142 P6, PLAN 7).
    raw = datetime_str.strip().rstrip(".")
    cleaned = raw[:-1] if raw.endswith("Z") else raw

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
        return datetime.fromisoformat(raw)
    except ValueError:
        pass

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
    """Express `dt` in the local timezone.

    An aware datetime is converted, preserving the instant. It used to have its
    tzinfo stripped and the same wall-clock digits relabelled as local, so an
    agent asked for `2025-09-10T14:00:00Z` booked 14:00 IST - five and a half
    hours out - and `modify_event_by_description` moved existing meetings by the
    same amount (NUMA-142 P6, PLAN 7).

    A naive datetime still means local wall clock, which is what the form
    payload in `_build_google_event_body` supplies.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(TIMEZONE)
    return dt.replace(tzinfo=TIMEZONE)


def _to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TIMEZONE)
    return dt.astimezone(TIMEZONE)


def _iso_to_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


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


def _current_month_window() -> Tuple[datetime, datetime]:
    """Return (month_start, month_end_exclusive) for the current calendar month."""
    now = datetime.now(TIMEZONE)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        month_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        month_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start, month_end
