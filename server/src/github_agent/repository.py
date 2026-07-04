"""GitHub data-access layer (NUMA-117, PLAN 6/18/21). SQL only.

Router wrapper functions keep their swallow/log semantics; these methods run the
raw SQL and raise on error.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from psycopg2.extras import Json

from ..core.base import BaseRepository
from ..core.db import get_db

_AUTH_UPSERT = (
    "INSERT INTO public.github_auth "
    "(user_id, github_username, github_user_id, access_token, scope, avatar_url, "
    " token_source, token_permissions, token_last_verified_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (user_id) DO UPDATE SET "
    "    github_username = EXCLUDED.github_username, "
    "    github_user_id = EXCLUDED.github_user_id, "
    "    access_token = EXCLUDED.access_token, "
    "    scope = EXCLUDED.scope, "
    "    avatar_url = EXCLUDED.avatar_url, "
    "    token_source = EXCLUDED.token_source, "
    "    token_permissions = EXCLUDED.token_permissions, "
    "    token_last_verified_at = EXCLUDED.token_last_verified_at, "
    "    updated_at = NOW()"
)


def _parse_github_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class GitHubRepository(BaseRepository):
    def get_access_token(self, user_id: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT access_token FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_username(self, user_id: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT github_username FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def all_user_ids(self) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM public.github_auth")
            return cur.fetchall() or []

    def upsert_auth(
        self, user_id: str, username: str, gh_user_id: int, access_token: str,
        scope: str, avatar_url: str, token_source: str, token_permissions: dict,
        verified_at: datetime,
    ) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                _AUTH_UPSERT,
                (
                    user_id, username, gh_user_id, access_token, scope, avatar_url,
                    token_source, Json(token_permissions), verified_at,
                ),
            )
            conn.commit()

    def get_status(self, user_id: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT github_username, avatar_url, scope "
                "FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()

    def disconnect(self, user_id: str) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM public.github_resource_snapshots WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM public.github_commits WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM public.github_repositories WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM public.github_auth WHERE user_id = %s", (user_id,))
            conn.commit()

    def cache_stats(self, user_id: str, repos: list, commits: list) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            for repo in repos:
                cur.execute(
                    "INSERT INTO public.github_repositories "
                    "(user_id, github_repo_id, name, full_name, owner_login, private, "
                    " fork, archived, disabled, language, stars, forks, open_issues, "
                    " default_branch, html_url, clone_url, pushed_at, updated_at_api, "
                    " permissions, raw_payload, last_synced_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) "
                    "ON CONFLICT (user_id, full_name) DO UPDATE SET "
                    "    github_repo_id = EXCLUDED.github_repo_id, "
                    "    name = EXCLUDED.name, "
                    "    owner_login = EXCLUDED.owner_login, "
                    "    private = EXCLUDED.private, "
                    "    fork = EXCLUDED.fork, "
                    "    archived = EXCLUDED.archived, "
                    "    disabled = EXCLUDED.disabled, "
                    "    language = EXCLUDED.language, "
                    "    stars = EXCLUDED.stars, "
                    "    forks = EXCLUDED.forks, "
                    "    open_issues = EXCLUDED.open_issues, "
                    "    default_branch = EXCLUDED.default_branch, "
                    "    html_url = EXCLUDED.html_url, "
                    "    clone_url = EXCLUDED.clone_url, "
                    "    pushed_at = EXCLUDED.pushed_at, "
                    "    updated_at_api = EXCLUDED.updated_at_api, "
                    "    permissions = EXCLUDED.permissions, "
                    "    raw_payload = EXCLUDED.raw_payload, "
                    "    last_synced_at = NOW()",
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
                    "INSERT INTO public.github_commits "
                    "(user_id, repo_full_name, sha, message, author_name, author_email, "
                    " author_login, committed_at, html_url, raw_payload, last_synced_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) "
                    "ON CONFLICT (user_id, repo_full_name, sha) DO UPDATE SET "
                    "    message = EXCLUDED.message, "
                    "    author_name = EXCLUDED.author_name, "
                    "    author_email = EXCLUDED.author_email, "
                    "    author_login = EXCLUDED.author_login, "
                    "    committed_at = EXCLUDED.committed_at, "
                    "    html_url = EXCLUDED.html_url, "
                    "    raw_payload = EXCLUDED.raw_payload, "
                    "    last_synced_at = NOW()",
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

    def cache_rows(self, user_id: str) -> Tuple:
        """Return (auth_row, repo_rows, commit_rows) for cached-stats assembly."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT avatar_url FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            auth_row = cur.fetchone()

            cur.execute(
                "SELECT name, full_name, private, language, stars, forks, "
                "       updated_at_api, html_url, last_synced_at "
                "FROM public.github_repositories WHERE user_id = %s "
                "ORDER BY COALESCE(pushed_at, updated_at_api, last_synced_at) DESC LIMIT 8",
                (user_id,),
            )
            repo_rows = cur.fetchall() or []

            cur.execute(
                "SELECT repo_full_name, sha, message, author_name, committed_at, html_url, last_synced_at "
                "FROM public.github_commits WHERE user_id = %s "
                "ORDER BY committed_at DESC NULLS LAST, last_synced_at DESC LIMIT 20",
                (user_id,),
            )
            commit_rows = cur.fetchall() or []
            return auth_row, repo_rows, commit_rows


github_repository = GitHubRepository()
