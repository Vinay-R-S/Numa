"""Regression tests for `slack_agent/config` (NUMA-142 P6).

Slack OAuth scopes. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


def test_slack_scopes_can_be_narrowed(monkeypatch):
    """The configured list was unioned with all 26 defaults, so it could only widen."""
    from src.slack_agent.config import _oauth_scopes

    monkeypatch.setenv("SLACK_BOT_SCOPES", "channels:read,channels:history,chat:write,users:read")
    assert _oauth_scopes().split(",") == [
        "channels:read", "channels:history", "chat:write", "users:read",
    ]


def test_slack_scopes_keep_the_scopes_the_app_calls(monkeypatch):
    """Narrowing must not drop the scopes the app itself needs to work."""
    from src.slack_agent.config import REQUIRED_SLACK_BOT_SCOPES, _oauth_scopes

    monkeypatch.setenv("SLACK_BOT_SCOPES", "channels:read")
    scopes = _oauth_scopes().split(",")

    for required in REQUIRED_SLACK_BOT_SCOPES:
        assert required in scopes


def test_slack_scopes_default_to_the_full_list(monkeypatch):
    from src.slack_agent.config import DEFAULT_SLACK_BOT_SCOPES, _oauth_scopes

    monkeypatch.delenv("SLACK_BOT_SCOPES", raising=False)
    assert _oauth_scopes().split(",") == list(DEFAULT_SLACK_BOT_SCOPES)
