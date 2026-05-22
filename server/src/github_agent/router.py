"""
GitHub Agent Router - OAuth connect/callback + stats + chat endpoints.
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from psycopg2.extras import Json

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from ..memory import memory_service
from .schemas import (
    GitHubAuthStatus,
    GitHubChatRequest,
    GitHubChatResponse,
    GitHubConnectResponse,
    GitHubTokenConnectRequest,
    GitHubUserStats,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["github"])

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

_oauth_states: dict[str, str] = {}

_TRANSIENT_DEPENDENCY_MARKERS = (
    "getaddrinfo failed",
    "could not translate host name",
    "name or service not known",
    "temporary failure in name resolution",
    "unable to find the server",
    "server closed the connection unexpectedly",
    "connection unexpectedly",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
)


def _is_transient_dependency_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_DEPENDENCY_MARKERS)


def _log_dependency_exception(message: str, exc: Exception, *args) -> None:
    if _is_transient_dependency_error(exc):
        log.debug(message, *args, exc)
    else:
        log.warning(message, *args, exc)

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


def _get_github_config():
    client_id = (os.getenv("GITHUB_CLIENT_ID") or os.getenv("ClientID", "")).strip()
    client_secret = (os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("ClientSecretKey", "")).strip()
    redirect_uri = os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        os.getenv("BACKEND_URL", "http://localhost:8000") + "/api/github/callback",
    ).strip()
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


def _token_permissions_from_headers(headers: httpx.Headers, *, source: str) -> dict:
    return {
        "source": source,
        "oauth_scopes": headers.get("x-oauth-scopes", ""),
        "accepted_permissions": headers.get("x-accepted-github-permissions", ""),
        "expected_repository_permissions": GITHUB_EXPECTED_TOKEN_PERMISSIONS,
    }


def _parse_github_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_all_connected_github_user_ids() -> list[str]:
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM public.github_auth")
        rows = cur.fetchall() or []
        cur.close()
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as exc:
        _log_dependency_exception("Could not list connected GitHub users: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def _store_github_stats_vector(user_id: str, stats: dict) -> None:
    try:
        repos = stats.get("recent_repos") or []
        commits = stats.get("recent_commits") or []
        repo_lines = []
        for repo in repos[:8]:
            if not isinstance(repo, dict):
                continue
            repo_lines.append(
                f"{repo.get('full_name') or repo.get('name')} "
                f"language={repo.get('language') or 'unknown'} "
                f"stars={repo.get('stars', 0)} updated={repo.get('updated_at') or 'unknown'}"
            )
        commit_lines = []
        for commit in commits[:8]:
            if not isinstance(commit, dict):
                continue
            commit_lines.append(
                f"{commit.get('repo')}: {commit.get('message') or 'commit'} "
                f"at {commit.get('date') or 'unknown'}"
            )

        text = (
            f"GitHub activity for {stats.get('username')}.\n"
            f"Commits today: {stats.get('total_commits_today', 0)}.\n"
            f"Commits this week: {stats.get('total_commits_week', 0)}.\n"
            f"Open pull requests: {stats.get('open_prs', 0)}.\n"
            f"Public repos: {stats.get('public_repos', 0)}. Private repos: {stats.get('private_repos', 0)}.\n"
            f"Followers: {stats.get('followers', 0)}. Following: {stats.get('following', 0)}.\n"
            f"Recent repositories: {'; '.join(repo_lines) if repo_lines else 'none'}.\n"
            f"Recent commits: {'; '.join(commit_lines) if commit_lines else 'none'}."
        )
        memory_service.upsert_domain_text(
            user_id=user_id,
            domain="github",
            stable_key="profile_stats",
            text=text,
            payload={
                "source": "github",
                "username": stats.get("username"),
                "total_commits_today": stats.get("total_commits_today", 0),
                "total_commits_week": stats.get("total_commits_week", 0),
                "open_prs": stats.get("open_prs", 0),
                "public_repos": stats.get("public_repos", 0),
                "private_repos": stats.get("private_repos", 0),
            },
        )
    except Exception as exc:
        _log_dependency_exception("GitHub Qdrant upsert failed: %s", exc)


def _cache_github_stats(user_id: str, stats: dict) -> None:
    repos = stats.get("recent_repos") or []
    commits = stats.get("recent_commits") or []
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        for repo in repos:
            cur.execute(
                """
                INSERT INTO public.github_repositories
                    (user_id, github_repo_id, name, full_name, owner_login, private,
                     fork, archived, disabled, language, stars, forks, open_issues,
                     default_branch, html_url, clone_url, pushed_at, updated_at_api,
                     permissions, raw_payload, last_synced_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, full_name) DO UPDATE SET
                    github_repo_id = EXCLUDED.github_repo_id,
                    name = EXCLUDED.name,
                    owner_login = EXCLUDED.owner_login,
                    private = EXCLUDED.private,
                    fork = EXCLUDED.fork,
                    archived = EXCLUDED.archived,
                    disabled = EXCLUDED.disabled,
                    language = EXCLUDED.language,
                    stars = EXCLUDED.stars,
                    forks = EXCLUDED.forks,
                    open_issues = EXCLUDED.open_issues,
                    default_branch = EXCLUDED.default_branch,
                    html_url = EXCLUDED.html_url,
                    clone_url = EXCLUDED.clone_url,
                    pushed_at = EXCLUDED.pushed_at,
                    updated_at_api = EXCLUDED.updated_at_api,
                    permissions = EXCLUDED.permissions,
                    raw_payload = EXCLUDED.raw_payload,
                    last_synced_at = NOW()
                """,
                (
                    user_id,
                    repo.get("github_repo_id"),
                    repo.get("name"),
                    repo.get("full_name"),
                    repo.get("owner_login"),
                    bool(repo.get("private", False)),
                    bool(repo.get("fork", False)),
                    bool(repo.get("archived", False)),
                    bool(repo.get("disabled", False)),
                    repo.get("language"),
                    int(repo.get("stars") or 0),
                    int(repo.get("forks") or 0),
                    int(repo.get("open_issues") or 0),
                    repo.get("default_branch"),
                    repo.get("html_url"),
                    repo.get("clone_url"),
                    _parse_github_dt(repo.get("pushed_at")),
                    _parse_github_dt(repo.get("updated_at")),
                    Json(repo.get("permissions") or {}),
                    Json(repo),
                ),
            )

        for commit in commits:
            sha = commit.get("full_sha") or commit.get("sha")
            if not sha or not commit.get("repo"):
                continue
            cur.execute(
                """
                INSERT INTO public.github_commits
                    (user_id, repo_full_name, sha, message, author_name, author_email,
                     author_login, committed_at, html_url, raw_payload, last_synced_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, repo_full_name, sha) DO UPDATE SET
                    message = EXCLUDED.message,
                    author_name = EXCLUDED.author_name,
                    author_email = EXCLUDED.author_email,
                    author_login = EXCLUDED.author_login,
                    committed_at = EXCLUDED.committed_at,
                    html_url = EXCLUDED.html_url,
                    raw_payload = EXCLUDED.raw_payload,
                    last_synced_at = NOW()
                """,
                (
                    user_id,
                    commit.get("repo"),
                    sha,
                    commit.get("message") or "",
                    commit.get("author"),
                    commit.get("author_email"),
                    commit.get("author_login"),
                    _parse_github_dt(commit.get("date")),
                    commit.get("html_url"),
                    Json(commit),
                ),
            )
        conn.commit()
        cur.close()
    except Exception as exc:
        _log_dependency_exception("GitHub DB cache update failed: %s", exc)
    finally:
        if conn:
            conn.close()


def _load_cached_github_stats(user_id: str, username: str) -> dict | None:
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT avatar_url
            FROM public.github_auth
            WHERE user_id = %s
            """,
            (user_id,),
        )
        auth_row = cur.fetchone()
        avatar_url = auth_row[0] if auth_row else None

        cur.execute(
            """
            SELECT name, full_name, private, language, stars, forks,
                   updated_at_api, html_url, last_synced_at
            FROM public.github_repositories
            WHERE user_id = %s
            ORDER BY COALESCE(pushed_at, updated_at_api, last_synced_at) DESC
            LIMIT 8
            """,
            (user_id,),
        )
        repo_rows = cur.fetchall() or []
        recent_repos = [
            {
                "name": row[0],
                "full_name": row[1],
                "private": bool(row[2]),
                "language": row[3],
                "stars": row[4] or 0,
                "forks": row[5] or 0,
                "updated_at": row[6].isoformat() if row[6] else None,
                "html_url": row[7],
            }
            for row in repo_rows
        ]
        repo_last_synced = [row[8] for row in repo_rows if row[8]]

        cur.execute(
            """
            SELECT repo_full_name, sha, message, author_name, committed_at, html_url, last_synced_at
            FROM public.github_commits
            WHERE user_id = %s
            ORDER BY committed_at DESC NULLS LAST, last_synced_at DESC
            LIMIT 20
            """,
            (user_id,),
        )
        commit_rows = cur.fetchall() or []
        recent_commits = [
            {
                "repo": row[0],
                "sha": (row[1] or "")[:12],
                "message": row[2] or "Commit",
                "author": row[3],
                "date": row[4].isoformat() if row[4] else None,
                "html_url": row[5],
            }
            for row in commit_rows
        ]
        commit_last_synced = [row[6] for row in commit_rows if row[6]]

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        total_commits_today = sum(
            1 for row in commit_rows if row[4] and row[4] >= today_start
        )
        total_commits_week = sum(
            1 for row in commit_rows if row[4] and row[4] >= week_start
        )

        if not recent_repos and not recent_commits:
            cur.close()
            return None

        last_synced_values = repo_last_synced + commit_last_synced
        last_synced_at = max(last_synced_values) if last_synced_values else None
        cur.close()
        return {
            "username": username,
            "avatar_url": avatar_url,
            "public_repos": sum(1 for repo in recent_repos if not repo["private"]),
            "private_repos": sum(1 for repo in recent_repos if repo["private"]),
            "followers": 0,
            "following": 0,
            "total_commits_today": total_commits_today,
            "total_commits_week": total_commits_week,
            "open_prs": 0,
            "recent_repos": recent_repos,
            "recent_commits": recent_commits,
            "_last_synced_at": last_synced_at,
        }
    except Exception as exc:
        _log_dependency_exception("Could not load cached GitHub stats: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def _cache_is_fresh(stats: dict | None, max_age_minutes: int = 10) -> bool:
    if not stats:
        return False
    last_synced = stats.get("_last_synced_at")
    if not isinstance(last_synced, datetime):
        return False
    return datetime.now(timezone.utc) - last_synced <= timedelta(minutes=max_age_minutes)


def _strip_internal_stats_fields(stats: dict) -> dict:
    cleaned = dict(stats)
    cleaned.pop("_last_synced_at", None)
    return cleaned


def fetch_and_store_github_stats_for_user(user_id: str) -> dict:
    token = _get_github_token(user_id)
    if not token:
        return {"ok": False, "detail": "GitHub not connected"}

    username = _get_github_username(user_id)
    if not username:
        return {"ok": False, "detail": "GitHub username not found"}

    from .github_client import GitHubClient
    client = GitHubClient(token)
    stats = client.get_contribution_stats(username)
    _cache_github_stats(user_id, stats)
    _store_github_stats_vector(user_id, stats)
    return {"ok": True, "username": username, "stats": stats}


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
        raise HTTPException(400, f"GitHub OAuth failed: {token_data.get('error_description', 'unknown')}")

    scope = token_data.get("scope", "")

    with httpx.Client(timeout=15) as client:
        user_resp = client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        gh_user = user_resp.json()
        token_permissions = _token_permissions_from_headers(user_resp.headers, source="oauth")

    username = gh_user.get("login", "")
    gh_user_id = gh_user.get("id", 0)
    avatar_url = gh_user.get("avatar_url", "")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.github_auth
                (user_id, github_username, github_user_id, access_token, scope, avatar_url,
                 token_source, token_permissions, token_last_verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                github_username = EXCLUDED.github_username,
                github_user_id  = EXCLUDED.github_user_id,
                access_token    = EXCLUDED.access_token,
                scope           = EXCLUDED.scope,
                avatar_url      = EXCLUDED.avatar_url,
                token_source    = EXCLUDED.token_source,
                token_permissions = EXCLUDED.token_permissions,
                token_last_verified_at = EXCLUDED.token_last_verified_at,
                updated_at      = NOW()
            """,
            (
                user_id,
                username,
                gh_user_id,
                access_token,
                scope,
                avatar_url,
                "oauth",
                Json(token_permissions),
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

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
            raise HTTPException(400, "GitHub token is invalid or expired")
        if not user_resp.is_success:
            raise HTTPException(400, "Could not verify GitHub token")
        gh_user = user_resp.json()
        scope = user_resp.headers.get("x-oauth-scopes", "")
        token_permissions = _token_permissions_from_headers(user_resp.headers, source="pat")

    username = gh_user.get("login", "")
    gh_user_id = gh_user.get("id", 0)
    avatar_url = gh_user.get("avatar_url", "")
    if not username or not gh_user_id:
        raise HTTPException(400, "GitHub token did not return a valid user")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.github_auth
                (user_id, github_username, github_user_id, access_token, scope, avatar_url,
                 token_source, token_permissions, token_last_verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                github_username = EXCLUDED.github_username,
                github_user_id  = EXCLUDED.github_user_id,
                access_token    = EXCLUDED.access_token,
                scope           = EXCLUDED.scope,
                avatar_url      = EXCLUDED.avatar_url,
                token_source    = EXCLUDED.token_source,
                token_permissions = EXCLUDED.token_permissions,
                token_last_verified_at = EXCLUDED.token_last_verified_at,
                updated_at      = NOW()
            """,
            (
                user_id,
                username,
                gh_user_id,
                access_token,
                scope,
                avatar_url,
                "pat",
                Json(token_permissions),
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    return GitHubAuthStatus(
        connected=True,
        github_username=username,
        avatar_url=avatar_url,
        scope=scope,
    )


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
        cur.execute("DELETE FROM public.github_resource_snapshots WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM public.github_commits WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM public.github_repositories WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM public.github_auth WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()


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
        from .github_client import GitHubClient
        client = GitHubClient(token)
        stats = client.get_contribution_stats(username)
        _cache_github_stats(user_id, stats)
        _store_github_stats_vector(user_id, stats)
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
