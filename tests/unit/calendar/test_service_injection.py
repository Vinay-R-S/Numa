"""Regression tests for `calendar/service` dependency injection (NUMA-143 P7).

`CalendarService` takes a `service_factory` so a test can supply a fake Google
client. The injection stopped at the repository boundary: `_delete_cal_event_
cleanup` built its own client with `get_calendar_service`, so a test that
swapped the factory still reached the real Google API (audit Low 7, PLAN 5.2).
"""
import inspect

import pytest


def test_cleanup_accepts_the_callers_service():
    """The seam itself: without this parameter the factory cannot reach here."""
    from src.calendar.repository import _delete_cal_event_cleanup

    assert "service" in inspect.signature(_delete_cal_event_cleanup).parameters


def test_every_cleanup_caller_passes_its_own_service():
    """A caller that omits it silently falls back to building a real client."""
    from src.calendar import service as calendar_service
    from src.calendar.agent import tools

    for module in (calendar_service, tools):
        source = inspect.getsource(module)
        for line_number, line in enumerate(source.splitlines(), 1):
            if "_delete_cal_event_cleanup(" not in line or "def " in line:
                continue
            # The call is either complete on this line or continues; in both
            # cases the argument must appear before the call closes.
            tail = "\n".join(source.splitlines()[line_number - 1:line_number + 4])
            assert "service=" in tail, (
                f"{module.__name__} line {line_number} calls the cleanup "
                f"without passing its service"
            )


def test_cleanup_uses_the_injected_service_and_never_builds_one(monkeypatch):
    """The behaviour, not just the signature."""
    from src.calendar import repository

    def fail_if_called(*args, **kwargs):
        raise AssertionError("built a real Google client despite an injected one")

    monkeypatch.setattr(repository, "get_calendar_service", fail_if_called)

    # A service whose every call raises sends the function down its documented
    # best-effort path without touching the network.
    class UnusableService:
        def events(self):
            raise RuntimeError("no network in tests")

    calls = {}

    def fake_primary_ids(service):
        calls["primary_ids"] = service
        return ["primary"]

    monkeypatch.setattr(repository, "_primary_calendar_ids", fake_primary_ids)
    # Stop before the database: the point here is which client was used.
    monkeypatch.setattr(repository, "_get_conn", lambda: (_ for _ in ()).throw(RuntimeError("no db")))

    repository._delete_cal_event_cleanup(
        "user-1", "primary", "event-1", service=UnusableService(),
    )

    assert isinstance(calls.get("primary_ids"), UnusableService)


def test_service_factory_is_injectable():
    from src.calendar.service import CalendarService

    assert "service_factory" in inspect.signature(CalendarService.__init__).parameters
