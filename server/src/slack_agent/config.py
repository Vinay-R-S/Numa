"""Slack configuration and OAuth URL helpers (NUMA-105 P3, PLAN 16.2).

Leaf module: env-based config only. Extracted verbatim from slack_agent/router.py;
router.py re-exports these names so callers are unaffected.
"""
import logging
import os
from urllib.parse import urlencode

from fastapi import HTTPException

from ..core.oauth_state import issue_state

log = logging.getLogger(__name__)


SIGNING_SECRET_ENV = "SLACK_SIGNING_SECRET"


def _signing_secret() -> str:
    return os.getenv(SIGNING_SECRET_ENV, "").strip()

def _client_id() -> str:
    return os.getenv("SLACK_CLIENT_ID", "").strip()

def _client_secret() -> str:
    return os.getenv("SLACK_CLIENT_SECRET", "").strip()

def _redirect_uri() -> str:
    return os.getenv("SLACK_REDIRECT_URI", "http://localhost:8000/slack/callback").strip()

def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").strip()

def _bot_token() -> str:
    return os.getenv("SLACK_BOT_TOKEN", "").strip()


def slack_is_configured() -> bool:
    """Whether this install talks to Slack at all (NUMA-129 P6, PLAN 8).

    Credentials, not the signing secret: `security.verify_signing_secret` asks
    this to decide whether a missing secret is a fresh install or a live
    integration whose webhook would go unverified.
    """
    return bool(_client_id() or _client_secret() or _bot_token())


DEFAULT_SLACK_BOT_SCOPES = [
    "app_mentions:read",
    "channels:history",
    "channels:join",
    "channels:manage",
    "channels:read",
    "channels:write.invites",
    "chat:write",
    "commands",
    "files:read",
    "files:write",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    "reactions:read",
    "reactions:write",
    "search:read.files",
    "search:read.public",
    "search:read.users",
    "team:read",
    "users:read",
    "users:read.email",
]


# Scopes this app calls Slack with directly: reading channels and history for the
# message list, resolving member names, and posting from the composer. An
# install without these does not fail at consent, it fails later at the feature,
# so they are the floor `SLACK_BOT_SCOPES` narrows down to rather than below
# (NUMA-142 P6 review).
REQUIRED_SLACK_BOT_SCOPES = [
    "channels:history",
    "channels:read",
    "chat:write",
    "users:read",
]


def _oauth_scopes() -> str:
    """The scopes to request: SLACK_BOT_SCOPES when set, the defaults otherwise.

    The configured list used to be unioned with all 26 defaults, so the variable
    could only ever widen the consent screen and never narrow it - an operator
    who set it to three read scopes still asked the workspace for every write
    scope in the list (NUMA-142 P6, PLAN 8). It narrows now, down to the scopes
    the app itself calls.
    """
    configured = os.getenv("SLACK_BOT_SCOPES", "").strip()
    scopes = [s.strip() for s in configured.split(",") if s.strip()] if configured else []
    if not scopes:
        return ",".join(DEFAULT_SLACK_BOT_SCOPES)

    missing = [scope for scope in REQUIRED_SLACK_BOT_SCOPES if scope not in scopes]
    if missing:
        log.warning(
            "SLACK_BOT_SCOPES omits scopes this app calls (%s); adding them to the request",
            ", ".join(missing),
        )
        scopes.extend(missing)

    return ",".join(scopes)


def _build_slack_authorization_url(user_id: str) -> str:
    cid = _client_id()
    if not cid:
        raise HTTPException(status_code=503, detail="SLACK_CLIENT_ID not configured")

    params = urlencode({
        "client_id":    cid,
        "scope":        _oauth_scopes(),
        "redirect_uri": _redirect_uri(),
        # Signed, not the bare user id. `state` is this flow's only CSRF token,
        # and the callback is an unauthenticated GET, so a plaintext id there
        # let a caller name any account to install into (NUMA-142 P6, PLAN 8).
        "state":        issue_state(user_id),
    })
    return f"https://slack.com/oauth/v2/authorize?{params}"
