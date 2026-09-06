"""Regression tests for `ai_settings/service` (NUMA-142 P6).

Integration-key .env writing. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


@pytest.mark.parametrize(
    "value",
    [
        # A newline started a second setting the next boot would load.
        "xoxb-1\nDATABASE_URL=postgresql://attacker@host/db",
        "a\rb",
        "a\x00b",
        # A quote closed the string early and merged two settings.
        "it's",
    ],
)
def test_env_value_injection_is_refused(value):
    from src.ai_settings.service import AISettingsSaveError, _validate_env_value

    with pytest.raises(AISettingsSaveError):
        _validate_env_value("slack_bot_token", value)


def test_env_value_accepts_a_windows_path():
    """Three integration keys are file paths; banning the backslash broke them."""
    from src.ai_settings.service import _env_line, _validate_env_value

    path = r"C:\Users\numa\token.json"
    _validate_env_value("strava_token_file", path)

    # Single-quoted, because dotenv decodes escape sequences inside double
    # quotes and would turn \numa into a newline and \token into a tab.
    assert _env_line("STRAVA_TOKEN_FILE", path) == f"STRAVA_TOKEN_FILE='{path}'"


def test_env_value_length_is_bounded():
    from src.ai_settings.service import AISettingsSaveError, _validate_env_value

    with pytest.raises(AISettingsSaveError):
        _validate_env_value("slack_bot_token", "x" * 10_000)
