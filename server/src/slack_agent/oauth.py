"""Slack OAuth v2 code exchange and connection completion (NUMA-115 P4, PLAN 2.1).

Moved verbatim out of the `/slack/callback` route so the router stays HTTP-only.
Failures are raised as `AppError` (mapped back to the same status codes by
`router._http_error`) instead of `HTTPException`, keeping the layer free of
FastAPI types.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from ..core.errors import AppError
from ..core.oauth_state import verify_state
from .config import _client_id, _client_secret, _frontend_url, _redirect_uri
from .events import fetch_latest_slack_for_user
from .persistence import _upsert_slack_auth

log = logging.getLogger(__name__)


async def exchange_oauth_code(code: str) -> dict:
    """Trade an OAuth code for workspace tokens. Raises AppError on failure."""
    cid = _client_id()
    csecret = _client_secret()
    if not cid or not csecret:
        raise AppError("Slack OAuth not fully configured", status_code=503)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": cid,
                "client_secret": csecret,
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
        )
    data = resp.json()

    if not data.get("ok"):
        raise AppError(f"Slack OAuth error: {data.get('error')}", status_code=400)

    return data


def frontend_redirect_url() -> str:
    return f"{_frontend_url()}/slack?connected=1"


async def complete_oauth_connection(code: str, state: str) -> str:
    """Exchange the code, persist the auth row, kick the first sync.

    `state` is the signed value issued by /connect; it is verified before it is
    trusted, because this route has no other authentication (NUMA-142 P6,
    PLAN 8). Returns the frontend URL to redirect to.
    """
    # Before the exchange, not after: an unverifiable state means this callback
    # is not ours, and there is no reason to spend a code exchange on it.
    user_id = verify_state(state)
    if not user_id:
        raise AppError("Invalid or expired OAuth state", status_code=400)

    data = await exchange_oauth_code(code)

    authed_user = data.get("authed_user", {})
    team = data.get("team", {})
    slack_user_id = authed_user.get("id", "")
    slack_team_id = team.get("id", "")
    bot_token_val = data.get("access_token", "")  # bot token is at root level
    user_token_val = authed_user.get("access_token", "")
    access_token = user_token_val or bot_token_val
    team_name = team.get("name")

    if access_token:
        _upsert_slack_auth(
            user_id=user_id,
            slack_user_id=slack_user_id,
            slack_team_id=slack_team_id,
            access_token=access_token,
            bot_token=bot_token_val or None,
            team_name=team_name,
            authed_user_obj=authed_user,
        )
        try:
            await asyncio.to_thread(fetch_latest_slack_for_user, user_id)
        except Exception as exc:
            log.warning("Slack initial sync after OAuth failed: %s", exc)

    return frontend_redirect_url()
