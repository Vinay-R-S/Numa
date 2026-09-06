"""Regression tests for `slack_agent/events` (NUMA-142 P6).

Slack event dedupe. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


def test_slack_event_is_processed_once():
    """A redelivery re-ran the LLM and reset a task the user had completed."""
    from src.slack_agent.events import _claim_event, _release_event

    event_id = "Ev-test-dedupe-1"
    _release_event(event_id)

    assert _claim_event(event_id) is True
    assert _claim_event(event_id) is False

    # A run that failed every attempt releases the id so a replay can retry.
    _release_event(event_id)
    assert _claim_event(event_id) is True
    _release_event(event_id)


def test_slack_event_without_an_id_is_never_suppressed():
    from src.slack_agent.events import _claim_event

    assert _claim_event("") is True
    assert _claim_event("") is True
