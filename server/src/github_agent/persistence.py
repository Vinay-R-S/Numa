"""GitHub persistence (NUMA-109 P3, PLAN 16.7).

Thin orchestration over GitHubRepository (Postgres cache) and the semantic memory
vector store. Keeps the best-effort swallow/log semantics the router relied on.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from ..core.timezones import user_timezone
from ..memory import memory_service
from .repository import github_repository
from .utils import _log_dependency_exception

log = logging.getLogger(__name__)


def _get_github_token(user_id: str) -> str | None:
    return github_repository.get_access_token(user_id)


def _get_github_username(user_id: str) -> str | None:
    return github_repository.get_username(user_id)


def get_connection_status(user_id: str):
    return github_repository.get_status(user_id)


def disconnect_github_user(user_id: str) -> None:
    github_repository.disconnect(user_id)


def get_all_connected_github_user_ids() -> list[str]:
    try:
        rows = github_repository.all_user_ids()
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as exc:
        _log_dependency_exception("Could not list connected GitHub users: %s", exc)
        return []


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


# Totals that describe the account rather than a repository or a commit. They
# come only from a live fetch, so the cached path had nothing to read and
# reported zeros (NUMA-142 P6, PLAN 7).
_PROFILE_STAT_KEYS = (
    "public_repos",
    "private_repos",
    "followers",
    "following",
    "open_prs",
)

# How long the cached stats are served before a live fetch is preferred. The
# cache had no freshness bound at all, so the zeros above were the steady state
# rather than a transient.
CACHE_FRESH_MINUTES = int(os.getenv("GITHUB_STATS_CACHE_MINUTES", "30"))


def _cache_github_stats(user_id: str, stats: dict) -> None:
    repos = stats.get("recent_repos") or []
    commits = stats.get("recent_commits") or []
    try:
        github_repository.cache_stats(user_id, repos, commits)
    except Exception as exc:
        _log_dependency_exception("GitHub DB cache update failed: %s", exc)

    try:
        github_repository.save_profile_stats(
            user_id,
            {key: int(stats.get(key) or 0) for key in _PROFILE_STAT_KEYS},
            datetime.now(timezone.utc),
        )
    except Exception as exc:
        _log_dependency_exception("GitHub profile stats cache update failed: %s", exc)


def _map_repo_rows(repo_rows: list) -> list[dict]:
    return [
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


def _map_commit_rows(commit_rows: list) -> list[dict]:
    return [
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


def _load_cached_github_stats(user_id: str, username: str) -> dict | None:
    try:
        auth_row, repo_rows, commit_rows = github_repository.cache_rows(user_id)
        avatar_url = auth_row[0] if auth_row else None
        profile_stats = (auth_row[1] if auth_row and len(auth_row) > 1 else None) or {}
        profile_synced_at = auth_row[2] if auth_row and len(auth_row) > 2 else None

        recent_repos = _map_repo_rows(repo_rows)
        recent_commits = _map_commit_rows(commit_rows)
        if not recent_repos and not recent_commits:
            return None

        # The user's midnight, not UTC's. The app's default timezone is
        # Asia/Kolkata, so "commits today" started 5.5 hours late and counted
        # the previous evening's commits as today's (NUMA-142 P6, PLAN 7).
        tz = user_timezone(user_id)
        today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        total_commits_today = sum(1 for row in commit_rows if row[4] and row[4] >= today_start)
        total_commits_week = sum(1 for row in commit_rows if row[4] and row[4] >= week_start)

        last_synced_values = [row[8] for row in repo_rows if row[8]] + [row[6] for row in commit_rows if row[6]]
        last_synced_at = max(last_synced_values) if last_synced_values else None
        # The stored totals from the last live fetch. Counting `recent_repos`
        # only ever counted the eight rows the cache query keeps.
        def total(key: str, fallback: int) -> int:
            value = profile_stats.get(key)
            return int(value) if isinstance(value, (int, float)) else fallback

        return {
            "username": username,
            "avatar_url": avatar_url,
            "public_repos": total(
                "public_repos", sum(1 for repo in recent_repos if not repo["private"]),
            ),
            "private_repos": total(
                "private_repos", sum(1 for repo in recent_repos if repo["private"]),
            ),
            "followers": total("followers", 0),
            "following": total("following", 0),
            "total_commits_today": total_commits_today,
            "total_commits_week": total_commits_week,
            "open_prs": total("open_prs", 0),
            "recent_repos": recent_repos,
            "recent_commits": recent_commits,
            "_last_synced_at": last_synced_at,
            "_profile_synced_at": profile_synced_at,
        }
    except Exception as exc:
        _log_dependency_exception("Could not load cached GitHub stats: %s", exc)
        return None
