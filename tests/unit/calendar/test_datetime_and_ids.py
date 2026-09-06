"""Regression tests for `calendar/google_client, calendar/datetime_utils` (NUMA-142 P6).

Calendar ids and offsets. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

from datetime import date, datetime, timedelta, timezone
import pytest


def test_calendar_event_id_round_trip():
    """A bare id is read as "primary", so a secondary calendar needs the prefix."""
    from src.calendar.google_client import _parse_calendar_event_id

    assert _parse_calendar_event_id("abc123") == ("primary", "abc123")
    assert _parse_calendar_event_id("team@group.calendar.google.com:abc123") == (
        "team@group.calendar.google.com",
        "abc123",
    )


def test_force_local_converts_an_offset_instead_of_relabelling_it():
    """An event asked for at 14:00Z was booked at 14:00 IST, 5.5 hours out."""
    from src.calendar.datetime_utils import TIMEZONE, force_local, parse_datetime

    aware = parse_datetime("2026-09-10T14:00:00Z")
    local = force_local(aware)

    assert local.tzinfo is not None
    # 14:00 UTC is 19:30 in Asia/Kolkata, not 14:00.
    assert local.utcoffset() == datetime.now(TIMEZONE).utcoffset()
    assert local.astimezone(timezone.utc).hour == 14
