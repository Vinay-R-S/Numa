"""
LeetCode GraphQL Client
========================
Fetches public user profile stats and recent submissions from LeetCode's
unofficial GraphQL API using httpx.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

log = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

PROFILE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      ranking
      reputation
      starRating
    }
    submitStats {
      acSubmissionNum {
        difficulty
        count
      }
      totalSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

RECENT_QUERY = """
query getRecentSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    title
    timestamp
    statusDisplay
    lang
  }
}
"""


class LeetCodeClient:
    """Thin wrapper around LeetCode's public GraphQL endpoint."""

    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout

    def _post(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com",
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_profile(self, username: str) -> Dict[str, Any]:
        """Fetch profile stats (ranking, reputation, solve counts)."""
        data = self._post(PROFILE_QUERY, {"username": username})
        user = (data.get("data") or {}).get("matchedUser")
        if not user:
            raise ValueError(f"LeetCode user '{username}' not found")
        return user

    def get_recent_submissions(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent accepted submissions."""
        data = self._post(RECENT_QUERY, {"username": username, "limit": limit})
        return (data.get("data") or {}).get("recentAcSubmissionList") or []

    def get_full_stats(self, username: str) -> Dict[str, Any]:
        """Combined profile + recent submissions as a flat dict matching LeetCodeStats."""
        profile = self.get_profile(username)
        recent = self.get_recent_submissions(username, limit=10)

        ac_stats = {
            item["difficulty"]: item["count"]
            for item in (profile.get("submitStats") or {}).get("acSubmissionNum") or []
        }
        total_stats = {
            item["difficulty"]: item["count"]
            for item in (profile.get("submitStats") or {}).get("totalSubmissionNum") or []
        }

        total_ac = ac_stats.get("All", 0)
        total_submitted = total_stats.get("All", 0)
        acceptance_rate = round((total_ac / total_submitted) * 100, 2) if total_submitted else 0.0

        prof = profile.get("profile") or {}

        return {
            "username": profile.get("username", username),
            "total_solved": total_ac,
            "easy_solved": ac_stats.get("Easy", 0),
            "medium_solved": ac_stats.get("Medium", 0),
            "hard_solved": ac_stats.get("Hard", 0),
            "acceptance_rate": acceptance_rate,
            "ranking": prof.get("ranking", 0) or 0,
            "contribution_points": 0,
            "reputation": prof.get("reputation", 0) or 0,
            "recent_submissions": [
                {
                    "title": s.get("title", ""),
                    "timestamp": s.get("timestamp", ""),
                    "status": s.get("statusDisplay", ""),
                    "lang": s.get("lang", ""),
                }
                for s in recent
            ],
        }
