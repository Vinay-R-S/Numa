"""GitHub persistence (NUMA-109 P3, PLAN 16.7).

Thin orchestration over GitHubRepository (Postgres cache) and the semantic memory
vector store. Keeps the best-effort swallow/log semantics the router relied on.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

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


def _cache_github_stats(user_id: str, stats: dict) -> None:
    repos = stats.get("recent_repos") or []
    commits = stats.get("recent_commits") or []
    try:
        github_repository.cache_stats(user_id, repos, commits)
    except Exception as exc:
        _log_dependency_exception("GitHub DB cache update failed: %s", exc)


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

        recent_repos = _map_repo_rows(repo_rows)
        recent_commits = _map_commit_rows(commit_rows)
        if not recent_repos and not recent_commits:
            return None

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        total_commits_today = sum(1 for row in commit_rows if row[4] and row[4] >= today_start)
        total_commits_week = sum(1 for row in commit_rows if row[4] and row[4] >= week_start)

        last_synced_values = [row[8] for row in repo_rows if row[8]] + [row[6] for row in commit_rows if row[6]]
        last_synced_at = max(last_synced_values) if last_synced_values else None
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
