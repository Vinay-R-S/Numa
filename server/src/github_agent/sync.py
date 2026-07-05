"""GitHub API orchestration (NUMA-109 P3, PLAN 16.7).

OAuth code exchange, personal-access-token verification, and live contribution
stats fetch-and-cache. Talks to the GitHub API (via GitHubClient / httpx) and
persists through persistence.py + GitHubRepository.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from .config import (
    GITHUB_TOKEN_URL,
    GITHUB_USER_URL,
    _get_github_config,
    _token_permissions_from_headers,
)
from .github_client import GitHubClient
from .persistence import (
    _cache_github_stats,
    _get_github_token,
    _get_github_username,
    _store_github_stats_vector,
)
from .repository import github_repository

log = logging.getLogger(__name__)


class GitHubConnectError(Exception):
    """Raised when an OAuth/PAT connection attempt fails validation."""


def connect_github_via_oauth(user_id: str, code: str) -> None:
    client_id, client_secret, redirect_uri = _get_github_config()
    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            GITHUB_TOKEN_URL,
            data=token_payload,
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise GitHubConnectError(
            f"GitHub OAuth failed: {token_data.get('error_description', 'unknown')}"
        )

    scope = token_data.get("scope", "")

    with httpx.Client(timeout=15) as client:
        user_resp = client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        gh_user = user_resp.json()
        token_permissions = _token_permissions_from_headers(user_resp.headers, source="oauth")

    github_repository.upsert_auth(
        user_id,
        gh_user.get("login", ""),
        gh_user.get("id", 0),
        access_token,
        scope,
        gh_user.get("avatar_url", ""),
        "oauth",
        token_permissions,
        datetime.now(timezone.utc),
    )


def connect_github_via_token(user_id: str, access_token: str) -> dict:
    with httpx.Client(timeout=15) as client:
        user_resp = client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if user_resp.status_code == 401:
            raise GitHubConnectError("GitHub token is invalid or expired")
        if not user_resp.is_success:
            raise GitHubConnectError("Could not verify GitHub token")
        gh_user = user_resp.json()
        scope = user_resp.headers.get("x-oauth-scopes", "")
        token_permissions = _token_permissions_from_headers(user_resp.headers, source="pat")

    username = gh_user.get("login", "")
    gh_user_id = gh_user.get("id", 0)
    avatar_url = gh_user.get("avatar_url", "")
    if not username or not gh_user_id:
        raise GitHubConnectError("GitHub token did not return a valid user")

    github_repository.upsert_auth(
        user_id, username, gh_user_id, access_token, scope, avatar_url,
        "pat", token_permissions, datetime.now(timezone.utc),
    )
    return {"connected": True, "github_username": username, "avatar_url": avatar_url, "scope": scope}


def fetch_live_github_stats(user_id: str, token: str, username: str) -> dict:
    client = GitHubClient(token)
    stats = client.get_contribution_stats(username)
    _cache_github_stats(user_id, stats)
    _store_github_stats_vector(user_id, stats)
    return stats


def fetch_and_store_github_stats_for_user(user_id: str) -> dict:
    token = _get_github_token(user_id)
    if not token:
        return {"ok": False, "detail": "GitHub not connected"}

    username = _get_github_username(user_id)
    if not username:
        return {"ok": False, "detail": "GitHub username not found"}

    stats = fetch_live_github_stats(user_id, token, username)
    return {"ok": True, "username": username, "stats": stats}
