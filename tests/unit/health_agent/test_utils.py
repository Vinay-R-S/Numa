"""Regression tests for `health_agent/utils` (NUMA-142 P6).

Health retention window. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

from datetime import date, datetime, timedelta, timezone
import pytest


def test_retention_window_is_one_constant():
    """The 8-day window was written out in four places and could drift apart."""
    from src.health_agent.service import DEFAULT_SNAPSHOT_DAYS
    from src.health_agent.utils import HEALTH_RETENTION_DAYS

    assert DEFAULT_SNAPSHOT_DAYS == HEALTH_RETENTION_DAYS


def test_activity_day_bounds_cover_a_whole_local_day():
    """The window ended at 23:59:59.999999 rather than the next midnight."""
    from zoneinfo import ZoneInfo

    from src.health_agent.utils import _activity_day_bounds

    tz = ZoneInfo("Asia/Kolkata")
    start, end = _activity_day_bounds(date(2026, 9, 6), tz)

    assert start == datetime(2026, 9, 6, 0, 0, tzinfo=tz)
    assert end == datetime(2026, 9, 7, 0, 0, tzinfo=tz)
    assert end - start == timedelta(days=1)
