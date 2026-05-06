"""
GitHub Agent Router - OAuth connect/callback + stats + chat endpoints.
"""
from __future__ import annotations

import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from .schemas import (
    GitHubAuthStatus,
    GitHubChatRequest,
    GitHubChatResponse,
    GitHubConnectResponse,
    GitHubUserStats,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["github"])

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

_oauth_states: dict[str, str] = {}


def _get_github_config():
    client_id = (os.getenv("GITHUB_CLIENT_ID") or os.getenv("ClientID", "")).strip()
    client_secret = (os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("ClientSecretKey", "")).strip()
    redirect_uri = os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        os.getenv("BACKEND_URL", "http://localhost:8000") + "/api/github/callback",
    )
    return client_id, client_secret, redirect_uri


def _get_github_token(user_id: str) -> str | None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token FROM public.github_auth WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        conn.close()


def _get_github_username(user_id: str) -> str | None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT github_username FROM public.github_auth WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        conn.close()


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

    client_id, client_secret, redirect_uri = _get_github_config()

    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(400, f"GitHub OAuth failed: {token_data.get('error_description', 'unknown')}")

    scope = token_data.get("scope", "")

    with httpx.Client(timeout=15) as client:
        user_resp = client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        gh_user = user_resp.json()

    username = gh_user.get("login", "")
    gh_user_id = gh_user.get("id", 0)
    avatar_url = gh_user.get("avatar_url", "")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.github_auth
                (user_id, github_username, github_user_id, access_token, scope, avatar_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                github_username = EXCLUDED.github_username,
                github_user_id  = EXCLUDED.github_user_id,
                access_token    = EXCLUDED.access_token,
                scope           = EXCLUDED.scope,
                avatar_url      = EXCLUDED.avatar_url,
                updated_at      = NOW()
            """,
            (user_id, username, gh_user_id, access_token, scope, avatar_url),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/settings?github=connected")


@router.get("/status", response_model=GitHubAuthStatus)
def github_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT github_username, avatar_url, scope FROM public.github_auth WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return GitHubAuthStatus(connected=False)
        return GitHubAuthStatus(
            connected=True,
            github_username=row[0],
            avatar_url=row[1],
            scope=row[2],
        )
    finally:
        conn.close()


@router.delete("/disconnect", status_code=204)
def disconnect_github(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM public.github_auth WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()


@router.get("/stats", response_model=GitHubUserStats)
def github_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    token = _get_github_token(user_id)
    if not token:
        raise HTTPException(400, "GitHub not connected. Go to Settings to connect.")

    username = _get_github_username(user_id)
    if not username:
        raise HTTPException(400, "GitHub username not found")

    from .github_client import GitHubClient
    client = GitHubClient(token)
    stats = client.get_contribution_stats(username)
    return GitHubUserStats(**stats)


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
