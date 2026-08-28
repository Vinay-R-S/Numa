"""AI settings constants (NUMA-119 P5, PLAN 2.1 / 10).

The router used to carry two hand-maintained dicts that were exact inverses of
each other (`_INTEGRATION_CHECK_KEYS` env -> api, `_INTEGRATION_ALLOWED_KEYS`
api -> env). One mapping is the source of truth now; the inverse is derived, so
the two can no longer drift. Insertion order matches the old check map, which
is the order the GET response is built in.
"""
from pathlib import Path

# Server-root .env, the file the integration-keys endpoints read and rewrite.
ENV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# api key (frontend field name) -> environment variable name.
INTEGRATION_KEYS: dict[str, str] = {
    "google_fit_client_id": "GOOGLE_FIT_CLIENT_ID",
    "google_fit_client_secret": "GOOGLE_FIT_CLIENT_SECRET",
    "google_fit_credentials_file": "GOOGLE_FIT_CREDENTIALS_FILE",
    "google_fit_token_file": "GOOGLE_FIT_TOKEN_FILE",
    "slack_client_id": "SLACK_CLIENT_ID",
    "slack_client_secret": "SLACK_CLIENT_SECRET",
    "slack_bot_token": "SLACK_BOT_TOKEN",
    "github_client_id": "GITHUB_CLIENT_ID",
    "github_client_secret": "GITHUB_CLIENT_SECRET",
    "github_oauth_redirect_uri": "GITHUB_OAUTH_REDIRECT_URI",
    "leetcode_username": "LEETCODE_USERNAME",
    "strava_client_id": "STRAVA_CLIENT_ID",
    "strava_client_secret": "STRAVA_CLIENT_SECRET",
    "strava_refresh_token": "STRAVA_REFRESH_TOKEN",
    "strava_token_file": "STRAVA_TOKEN_FILE",
}

# Keys whose value is not a secret, so the GET response echoes it back as
# `<key>_value` for the UI to prefill.
NON_SECRET_KEYS: tuple[str, ...] = (
    "leetcode_username",
    "github_oauth_redirect_uri",
    "google_fit_credentials_file",
    "google_fit_token_file",
    "strava_token_file",
)
