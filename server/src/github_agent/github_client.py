"""
GitHub API v3 client - fetches user stats, commits, PRs, and repos.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_TIMEOUT = httpx.Timeout(connect=3.0, read=6.0, write=3.0, pool=3.0)


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
        with httpx.Client(timeout=GITHUB_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def get_user(self) -> dict:
        return self._get("/user")

    def get_repos(self, sort: str = "updated", per_page: int = 10) -> list[dict]:
        repos = self._get("/user/repos", {"sort": sort, "per_page": per_page, "type": "all"})
        return [
            {
                "github_repo_id": r.get("id"),
                "name": r["name"],
                "full_name": r["full_name"],
                "owner_login": (r.get("owner") or {}).get("login"),
                "private": r["private"],
                "fork": r.get("fork", False),
                "archived": r.get("archived", False),
                "disabled": r.get("disabled", False),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "open_issues": r.get("open_issues_count", 0),
                "default_branch": r.get("default_branch"),
                "updated_at": r.get("updated_at"),
                "pushed_at": r.get("pushed_at"),
                "html_url": r.get("html_url"),
                "clone_url": r.get("clone_url"),
                "permissions": r.get("permissions") or {},
            }
            for r in repos
        ]

    def get_recent_commits(self, per_repo: int = 2, repo_limit: int = 5) -> list[dict]:
        """Fetch recent commits from repos the token can access, including private repos."""
        commits: list[dict] = []
        repos = self._get(
            "/user/repos",
            {"sort": "pushed", "per_page": repo_limit, "type": "all"},
        )

        def fetch_repo_commits(repo: dict) -> list[dict]:
            full_name = repo.get("full_name")
            if not full_name:
                return []
            try:
                repo_commits = self._get(f"/repos/{full_name}/commits", {"per_page": per_repo})
            except Exception as exc:
                log.warning("Failed to fetch commits for %s: %s", full_name, exc)
                return []

            rows = []
            for commit in repo_commits:
                commit_data = commit.get("commit", {})
                author_data = commit_data.get("author") or {}
                rows.append(
                    {
                        "sha": commit.get("sha", "")[:12],
                        "full_sha": commit.get("sha", ""),
                        "message": (commit_data.get("message") or "").splitlines()[0],
                        "repo": full_name,
                        "author": author_data.get("name"),
                        "author_email": author_data.get("email"),
                        "author_login": (commit.get("author") or {}).get("login"),
                        "date": author_data.get("date"),
                        "html_url": commit.get("html_url"),
                    }
                )
            return rows

        with ThreadPoolExecutor(max_workers=min(5, len(repos) or 1)) as executor:
            futures = [executor.submit(fetch_repo_commits, repo) for repo in repos]
            for future in as_completed(futures):
                try:
                    commits.extend(future.result())
                except Exception as exc:
                    log.warning("Failed to collect GitHub commits: %s", exc)

        return sorted(commits, key=lambda item: item.get("date") or "", reverse=True)[:20]

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

        jobs = {
            "user": lambda: self.get_user(),
            "repos": lambda: self.get_repos(per_page=8),
            "commits_today": lambda: self.get_commits_count(username, today_start),
            "commits_week": lambda: self.get_commits_count(username, week_start),
            "open_prs": lambda: self.get_open_prs(username),
            "recent_commits": lambda: self.get_recent_commits(),
        }
        results: dict = {}
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            future_map = {executor.submit(fn): name for name, fn in jobs.items()}
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    log.warning("GitHub stats segment failed (%s): %s", name, exc)

        user = results.get("user") or {}
        repos = results.get("repos") or []
        commits_today = int(results.get("commits_today") or 0)
        commits_week = int(results.get("commits_week") or 0)
        open_prs = results.get("open_prs") or []
        recent_commits = results.get("recent_commits") or []

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
            "recent_commits": recent_commits,
        }
