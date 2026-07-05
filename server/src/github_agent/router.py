"""
GitHub Agent Router - OAuth connect/callback + stats + chat endpoints.

Thin routing layer (NUMA-109 P3, PLAN 16.7): OAuth config lives in config.py,
DB/vector persistence in persistence.py, GitHub API orchestration in sync.py, the
sub-agent in service.py. Names re-exported below preserve existing import paths.
"""
from __future__ import annotations

import logging
import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..auth.dependencies import get_current_user
from .config import (
    GITHUB_OAUTH_URL,
    _get_github_config,
    _oauth_states,
)
from .persistence import (
    _get_github_token,
    _get_github_username,
    _load_cached_github_stats,
    disconnect_github_user,
    get_all_connected_github_user_ids,
    get_connection_status,
)
from .schemas import (
    GitHubAuthStatus,
    GitHubChatRequest,
    GitHubChatResponse,
    GitHubConnectResponse,
    GitHubTokenConnectRequest,
    GitHubUserStats,
)
from .sync import (
    GitHubConnectError,
    connect_github_via_oauth,
    connect_github_via_token,
    fetch_and_store_github_stats_for_user,
    fetch_live_github_stats,
)
from .utils import _strip_internal_stats_fields

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["github"])

# Backwards-compatible re-exports (auth.router and core.data_sync import these).
__all__ = [
    "router",
    "GITHUB_OAUTH_URL",
    "_get_github_config",
    "_get_github_token",
    "_oauth_states",
    "fetch_and_store_github_stats_for_user",
    "get_all_connected_github_user_ids",
]


@router.get("/connect", response_model=GitHubConnectResponse)
def connect_github(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    client_id, _, redirect_uri = _get_github_config()
    if not client_id:
        raise HTTPException(500, "GITHUB_CLIENT_ID not configured")

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = user_id

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "repo read:user user:email",
        "state": state,
    }
    return GitHubConnectResponse(authorization_url=f"{GITHUB_OAUTH_URL}?{urlencode(params)}")


@router.get("/callback")
def github_callback(code: str = Query(...), state: str = Query(...)):
    user_id = _oauth_states.pop(state, None)
    if not user_id:
        raise HTTPException(400, "Invalid or expired OAuth state")

    try:
        connect_github_via_oauth(user_id, code)
    except GitHubConnectError as exc:
        raise HTTPException(400, str(exc))

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/settings?github=connected")


@router.post("/connect-token", response_model=GitHubAuthStatus)
def connect_github_token(
    body: GitHubTokenConnectRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    access_token = body.access_token.strip()
    if not access_token:
        raise HTTPException(400, "GitHub token is required")

    try:
        status = connect_github_via_token(user_id, access_token)
    except GitHubConnectError as exc:
        raise HTTPException(400, str(exc))

    return GitHubAuthStatus(**status)


@router.get("/status", response_model=GitHubAuthStatus)
def github_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    row = get_connection_status(user_id)
    if not row:
        return GitHubAuthStatus(connected=False)
    return GitHubAuthStatus(
        connected=True,
        github_username=row[0],
        avatar_url=row[1],
        scope=row[2],
    )


@router.delete("/disconnect", status_code=204)
def disconnect_github(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    disconnect_github_user(user_id)


@router.get("/stats", response_model=GitHubUserStats)
def github_stats(
    force: bool = Query(False, description="Force a live GitHub API refresh"),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    token = _get_github_token(user_id)
    if not token:
        raise HTTPException(400, "GitHub not connected. Go to Settings to connect.")

    username = _get_github_username(user_id)
    if not username:
        raise HTTPException(400, "GitHub username not found")

    cached = _load_cached_github_stats(user_id, username)
    if cached and not force:
        return GitHubUserStats(**_strip_internal_stats_fields(cached))

    try:
        stats = fetch_live_github_stats(user_id, token, username)
        return GitHubUserStats(**stats)
    except Exception as exc:
        log.warning("Live GitHub stats fetch failed: %s", exc)
        if cached:
            return GitHubUserStats(**_strip_internal_stats_fields(cached))
        raise HTTPException(504, "GitHub took too long to respond. Try again in a moment.")


@router.post("/chat", response_model=GitHubChatResponse)
def github_chat(body: GitHubChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    from .service import run_github_agent_chat
    result = run_github_agent_chat(
        query=body.query,
        history=[m.model_dump() for m in body.history],
        user_id=user_id,
    )
    return GitHubChatResponse(**result)
