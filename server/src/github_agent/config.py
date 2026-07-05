"""GitHub OAuth configuration and constants (NUMA-109 P3, PLAN 16.7).

OAuth endpoint URLs, expected token permissions, in-memory OAuth state store, and
config/header helpers. No DB, no business logic.
"""
from __future__ import annotations

import os

import httpx

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# OAuth state -> user_id, set on /connect and consumed on /callback.
_oauth_states: dict[str, str] = {}

GITHUB_EXPECTED_TOKEN_PERMISSIONS = {
    "actions": "read",
    "commit_statuses": "read",
    "contents": "read",
    "deployments": "read",
    "discussions": "read",
    "environments": "read",
    "issues": "read",
    "metadata": "read",
    "packages": "read",
    "pages": "read",
    "projects": "read",
    "pull_requests": "read",
    "security_events": "read",
    "webhooks": "read",
}


def _get_github_config() -> tuple[str, str, str]:
    client_id = (os.getenv("GITHUB_CLIENT_ID") or os.getenv("ClientID", "")).strip()
    client_secret = (os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("ClientSecretKey", "")).strip()
    redirect_uri = os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        os.getenv("BACKEND_URL", "http://localhost:8000") + "/api/github/callback",
    ).strip()
    return client_id, client_secret, redirect_uri


def _token_permissions_from_headers(headers: httpx.Headers, *, source: str) -> dict:
    return {
        "source": source,
        "oauth_scopes": headers.get("x-oauth-scopes", ""),
        "accepted_permissions": headers.get("x-accepted-github-permissions", ""),
        "expected_repository_permissions": GITHUB_EXPECTED_TOKEN_PERMISSIONS,
    }
