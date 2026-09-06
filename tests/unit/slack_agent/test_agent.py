"""Regression tests for `slack_agent/agent` (NUMA-142 P6).

Slack task extraction. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

from datetime import date, datetime, timedelta, timezone
import pytest


def test_slack_task_title_strips_either_politeness_order():
    """The fourth regex was unreachable: its prefix was stripped two lines earlier."""
    from src.slack_agent.agent import _slack_task_title

    # Both orders reduce to the same title (the helper capitalises it).
    assert _slack_task_title("please can you send the report") == "Send the report"
    assert _slack_task_title("can you please send the report") == "Send the report"


def test_slack_due_date_uses_a_timezone_aware_datetime():
    """The due date was built in UTC, so "by 5pm" from an IST user became 22:30."""
    from src.slack_agent.agent import _parse_slack_due

    due = _parse_slack_due("finish the deck by 5pm")
    assert due is not None
    assert due.tzinfo is not None
    assert (due.hour, due.minute) == (17, 0)
