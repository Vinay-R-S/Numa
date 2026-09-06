import os
from urllib.parse import parse_qs, urlparse, urlunparse

import pytest


SECRET_TESTS_ENABLED = os.getenv("RUN_SECRET_INTEGRATION_TESTS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

pytestmark = pytest.mark.skipif(
    not SECRET_TESTS_ENABLED,
    reason="Set RUN_SECRET_INTEGRATION_TESTS=1 in GitHub Secrets to run secret-backed config tests.",
)

VALUE_ONLY_REQUIRED_ENV_VARS = {
    "BACKEND_URL",
    "DATABASE_URL",
    "FRONTEND_URL",
    "GOOGLE_FIT_CLIENT_ID",
    "GOOGLE_FIT_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "GOOGLE_OAUTH_SUCCESS_REDIRECT",
    "JWT_SECRET",
    "QDRANT_API_KEY",
    "QDRANT_URL_ENDPOINT",
    "SLACK_BOT_SCOPES",
    "SLACK_BOT_TOKEN",
    "SLACK_CLIENT_ID",
    "SLACK_CLIENT_SECRET",
    "SLACK_MESSAGE_RETENTION_DAYS",
    "SLACK_OAUTH_TOKEN",
    "SLACK_REDIRECT_URI",
    "SLACK_SIGNING_SECRET",
    "SLACK_USER_OAUTH_TOKEN",
    "STRAVA_ACCESS_TOKEN",
    "STRAVA_AUTH_CODE",
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REFRESH_TOKEN",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_URL",
}

FILE_OR_LOCAL_STATE_ENV_VARS = {
    "GOOGLE_CALENDAR_CREDENTIALS_FILE",
    "GOOGLE_CALENDAR_TOKEN_DIR",
    "STRAVA_TOKEN_FILE",
}

URL_ENV_VARS = {
    "BACKEND_URL",
    "FRONTEND_URL",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "GOOGLE_OAUTH_SUCCESS_REDIRECT",
    "QDRANT_URL_ENDPOINT",
    "SLACK_REDIRECT_URI",
    "SUPABASE_URL",
}

SECRET_LIKE_ENV_VARS = {
    name
    for name in VALUE_ONLY_REQUIRED_ENV_VARS
    if any(part in name for part in ("KEY", "SECRET", "TOKEN", "JWT", "DATABASE_URL", "AUTH_CODE"))
}


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _missing(names: set[str]) -> list[str]:
    return sorted(name for name in names if not _env(name))


def _parsed_url(name: str):
    parsed = urlparse(_env(name))
    assert parsed.scheme in {"http", "https", "postgresql", "postgres"}, f"{name} must use a valid URL scheme"
    assert parsed.netloc, f"{name} must include a host"
    return parsed


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if parsed.username or parsed.password:
        netloc = f"***:***@{hostname}{port}"
    else:
        netloc = parsed.netloc
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def test_secret_config_required_value_only_variables_are_present():
    missing = _missing(VALUE_ONLY_REQUIRED_ENV_VARS)

    assert missing == []


def test_secret_config_file_path_variables_are_not_required_by_ci_suite():
    assert VALUE_ONLY_REQUIRED_ENV_VARS.isdisjoint(FILE_OR_LOCAL_STATE_ENV_VARS)


def test_secret_config_urls_are_parseable_and_network_ready():
    for name in URL_ENV_VARS:
        parsed = _parsed_url(name)
        assert parsed.fragment == "", f"{name} must not include URL fragments"


def test_secret_config_database_url_can_be_parsed_and_redacted():
    parsed = _parsed_url("DATABASE_URL")

    assert parsed.scheme in {"postgresql", "postgres"}
    assert parsed.hostname
    assert parsed.username
    assert parsed.password

    redacted = _redact_url(_env("DATABASE_URL"))
    assert parsed.password not in redacted
    assert parsed.username not in redacted
    assert "***:***@" in redacted


def test_secret_config_provider_groups_are_complete():
    groups = {
        "google_fit": {"GOOGLE_FIT_CLIENT_ID", "GOOGLE_FIT_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI"},
        "qdrant": {"QDRANT_URL_ENDPOINT", "QDRANT_API_KEY"},
        "slack": {
            "SLACK_CLIENT_ID",
            "SLACK_CLIENT_SECRET",
            "SLACK_SIGNING_SECRET",
            "SLACK_BOT_TOKEN",
            "SLACK_OAUTH_TOKEN",
            "SLACK_USER_OAUTH_TOKEN",
            "SLACK_REDIRECT_URI",
        },
        "strava": {"STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_ACCESS_TOKEN", "STRAVA_REFRESH_TOKEN"},
        "supabase": {"SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"},
    }

    incomplete_groups = {
        group_name: _missing(group_vars)
        for group_name, group_vars in groups.items()
        if _missing(group_vars)
    }

    assert incomplete_groups == {}


def test_secret_config_values_are_not_placeholders():
    placeholder_fragments = {
        "changeme",
        "example",
        "fake",
        "placeholder",
        "replace_me",
        "todo",
        "your_",
    }

    placeholder_vars = [
        name
        for name in VALUE_ONLY_REQUIRED_ENV_VARS
        if any(fragment in _env(name).lower() for fragment in placeholder_fragments)
    ]

    assert placeholder_vars == []


def test_secret_config_secret_like_values_have_reasonable_entropy():
    weak_values = []
    for name in SECRET_LIKE_ENV_VARS:
        value = _env(name)
        unique_chars = set(value)
        if len(value) < 12 or len(unique_chars) < 6:
            weak_values.append(name)

    assert weak_values == []


def test_secret_config_oauth_redirects_have_no_inline_secrets():
    redirect_names = {"GOOGLE_OAUTH_REDIRECT_URI", "GOOGLE_OAUTH_SUCCESS_REDIRECT", "SLACK_REDIRECT_URI"}
    blocked_query_keys = {"token", "access_token", "refresh_token", "client_secret", "api_key"}

    unsafe_redirects = []
    for name in redirect_names:
        parsed = _parsed_url(name)
        query_keys = set(parse_qs(parsed.query))
        if query_keys.intersection(blocked_query_keys):
            unsafe_redirects.append(name)

    assert unsafe_redirects == []


def test_secret_config_slack_scopes_are_well_formed():
    scopes = [scope.strip() for scope in _env("SLACK_BOT_SCOPES").replace(",", " ").split()]

    assert scopes
    assert all(":" in scope for scope in scopes)
    assert len(scopes) == len(set(scopes))


def test_secret_config_slack_retention_days_is_positive_integer():
    retention_days = int(_env("SLACK_MESSAGE_RETENTION_DAYS"))

    assert 1 <= retention_days <= 3650
