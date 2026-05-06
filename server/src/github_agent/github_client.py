"""
GitHub API v3 client - fetches user stats, commits, PRs, and repos.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, access_token: str):
        self.token = access_token
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> dict | list:
        url = f"{GITHUB_API}{path}"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def get_user(self) -> dict:
        return self._get("/user")

    def get_repos(self, sort: str = "updated", per_page: int = 10) -> list[dict]:
        repos = self._get("/user/repos", {"sort": sort, "per_page": per_page, "type": "all"})
        return [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "private": r["private"],
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "updated_at": r.get("updated_at"),
                "html_url": r.get("html_url"),
            }
            for r in repos
        ]

    def get_commits_count(self, username: str, since: datetime) -> int:
        """Count commits across all repos since a given date using the search API."""
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            result = self._get(
                "/search/commits",
                {"q": f"author:{username} committer-date:>={since_str}", "per_page": 1},
            )
            return result.get("total_count", 0)
        except Exception as exc:
            log.warning("Failed to count commits: %s", exc)
            return 0

    def get_open_prs(self, username: str) -> list[dict]:
        """Get open PRs authored by the user."""
        try:
            result = self._get(
                "/search/issues",
                {"q": f"is:pr is:open author:{username}", "per_page": 10},
            )
            items = result.get("items", [])
            return [
                {
                    "title": pr["title"],
                    "repo": pr["repository_url"].split("/")[-1] if "repository_url" in pr else "",
                    "html_url": pr.get("html_url"),
                    "created_at": pr.get("created_at"),
                    "state": pr.get("state"),
                }
                for pr in items
            ]
        except Exception as exc:
            log.warning("Failed to fetch open PRs: %s", exc)
            return []

    def get_recent_activity(self, username: str, per_page: int = 30) -> list[dict]:
        """Get recent public events for the user."""
        try:
            events = self._get(f"/users/{username}/events", {"per_page": per_page})
            return [
                {
                    "type": e["type"],
                    "repo": e.get("repo", {}).get("name", ""),
                    "created_at": e.get("created_at"),
                    "payload_action": e.get("payload", {}).get("action"),
                }
                for e in events
            ]
        except Exception:
            return []

    def get_contribution_stats(self, username: str) -> dict:
        """Get aggregated contribution stats."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        user = self.get_user()
        repos = self.get_repos(per_page=10)
        commits_today = self.get_commits_count(username, today_start)
        commits_week = self.get_commits_count(username, week_start)
        open_prs = self.get_open_prs(username)

        return {
            "username": username,
            "avatar_url": user.get("avatar_url"),
            "public_repos": user.get("public_repos", 0),
            "private_repos": user.get("total_private_repos", 0) or user.get("owned_private_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "total_commits_today": commits_today,
            "total_commits_week": commits_week,
            "open_prs": len(open_prs),
            "recent_repos": repos,
        }
