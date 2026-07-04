"""Slack configuration and OAuth URL helpers (NUMA-105 P3, PLAN 16.2).

Leaf module: env-based config only. Extracted verbatim from slack_agent/router.py;
router.py re-exports these names so callers are unaffected.
"""
import os
from urllib.parse import urlencode

from fastapi import HTTPException


def _signing_secret() -> str:
    return os.getenv("SLACK_SIGNING_SECRET", "").strip()

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


def _oauth_scopes() -> str:
    configured = os.getenv("SLACK_BOT_SCOPES", "").strip()
    scopes = [s.strip() for s in configured.split(",") if s.strip()] if configured else []
    for scope in DEFAULT_SLACK_BOT_SCOPES:
        if scope not in scopes:
            scopes.append(scope)
    return ",".join(scopes)


def _build_slack_authorization_url(user_id: str) -> str:
    cid = _client_id()
    if not cid:
        raise HTTPException(status_code=503, detail="SLACK_CLIENT_ID not configured")

    params = urlencode({
        "client_id":    cid,
        "scope":        _oauth_scopes(),
        "redirect_uri": _redirect_uri(),
        "state":        user_id,
    })
    return f"https://slack.com/oauth/v2/authorize?{params}"
