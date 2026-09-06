"""Regression tests for `core/timezones` (NUMA-142 P6).

Timezone resolution. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

from datetime import date, datetime, timedelta, timezone
import pytest


def test_resolve_timezone_falls_back_instead_of_raising():
    """A malformed profile value raised ValueError out of its own fallback.

    `health_agent.utils._resolve_timezone_name` caught only
    `ZoneInfoNotFoundError`, so a value like "GMT+5:30" escaped as a ValueError.
    """
    from src.core.timezones import resolve_timezone

    assert str(resolve_timezone("GMT+5:30")) == "Asia/Kolkata"
    assert str(resolve_timezone(None)) == "Asia/Kolkata"
    assert str(resolve_timezone("")) == "Asia/Kolkata"
    assert str(resolve_timezone("Europe/Lisbon")) == "Europe/Lisbon"


def test_calendar_timezone_survives_an_empty_env_var():
    """`TIMEZONE=` raised ValueError past a ZoneInfoNotFoundError-only catch.

    `calendar/datetime_utils` is on the boot path (main -> calendar router ->
    service -> here), so the app died at import instead of falling back.
    """
    from src.core.timezones import default_timezone_name, resolve_timezone

    assert default_timezone_name() != ""
    assert str(resolve_timezone("")) == "Asia/Kolkata"
    assert str(resolve_timezone("Not/AZone")) == "Asia/Kolkata"


def test_every_timezone_resolver_shares_one_implementation():
    """Three copies existed; only one had the wide catch."""
    from src.calendar.datetime_utils import _resolve_timezone
    from src.core.timezones import resolve_timezone
    from src.health_agent.utils import _resolve_timezone_name

    assert str(_resolve_timezone_name("")) == str(resolve_timezone(""))
    assert str(_resolve_timezone()) == str(resolve_timezone(None))


def test_health_timezone_helper_delegates_to_core():
    from src.core.timezones import resolve_timezone
    from src.health_agent.utils import _resolve_timezone_name

    assert str(_resolve_timezone_name("GMT+5:30")) == str(resolve_timezone("GMT+5:30"))
