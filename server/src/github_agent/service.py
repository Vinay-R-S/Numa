"""GitHub feature service (NUMA-117 P4, PLAN 2.1 / 5.2 / 21.1).

`GitHubService` owns the orchestration that used to sit inside the HTTP routes:
the OAuth authorization URL and state handshake, the two connect paths (OAuth
code exchange and personal access token), the connection status roll-up, the
disconnect, and the stats read with its cache-first / live-fetch / fall-back-to-
cache ladder. Dependencies (persistence readers, sync callables, the OAuth state
store and the agent entrypoint) are injected through the constructor.

The LangGraph sub-agent moved to `agent.py`; its public entrypoint is re-exported
here so `master_agent.orchestrator` keeps its existing import path.

Errors: methods raise `core.errors.AppError` with the status code the route used
to raise directly; `router._http_error` maps them back to HTTP.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode

from ..core.base import BaseService
from ..core.errors import AppError
from .agent import (  # noqa: F401  re-exported for existing import paths
    GITHUB_AGENT_SYSTEM_PROMPT,
    GitHubAgentState,
    run_github_agent_chat,
)
from ..core.oauth_state import OAuthStateError, issue_state, verify_state
from .config import GITHUB_OAUTH_URL, _get_github_config
from .persistence import (
    CACHE_FRESH_MINUTES,
    _get_github_token,
    _get_github_username,
    _load_cached_github_stats,
    disconnect_github_user,
    get_connection_status,
)
from .schemas import GitHubUserStats
from .sync import (
    GitHubConnectError,
    connect_github_via_oauth,
    connect_github_via_token,
    fetch_live_github_stats,
)
from .utils import _strip_internal_stats_fields

OAUTH_SCOPES = "repo read:user user:email"


def _is_cache_fresh(cached: Dict) -> bool:
    """True while the cached stats are recent enough to serve without a fetch.

    The cache had no freshness bound, so the stored snapshot was served on every
    load forever and a forced refresh's numbers reverted immediately.
    """
    synced_at = cached.get("_profile_synced_at") or cached.get("_last_synced_at")
    if not isinstance(synced_at, datetime):
        return False
    if synced_at.tzinfo is None:
        synced_at = synced_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - synced_at < timedelta(minutes=CACHE_FRESH_MINUTES)


class GitHubService(BaseService):
    """GitHub connection and contribution stats behind the /api/github routes."""

    def __init__(
        self,
        read_token: Optional[Callable[[str], Optional[str]]] = None,
        read_username: Optional[Callable[[str], Optional[str]]] = None,
        read_status: Optional[Callable[[str], Optional[tuple]]] = None,
        read_cached_stats: Optional[Callable[[str, str], Optional[Dict]]] = None,
        disconnect_user: Optional[Callable[[str], None]] = None,
        oauth_config: Optional[Callable[[], tuple]] = None,
        connect_oauth: Optional[Callable[[str, str], None]] = None,
        connect_token: Optional[Callable[[str, str], Dict]] = None,
        fetch_live_stats: Optional[Callable[[str, str, str], Dict]] = None,
        chat_agent: Optional[Callable[..., Dict]] = None,
    ) -> None:
        super().__init__()
        self.read_token = read_token or _get_github_token
        self.read_username = read_username or _get_github_username
        self.read_status = read_status or get_connection_status
        self.read_cached_stats = read_cached_stats or _load_cached_github_stats
        self.disconnect_user = disconnect_user or disconnect_github_user
        self.oauth_config = oauth_config or _get_github_config
        self.connect_oauth = connect_oauth or connect_github_via_oauth
        self.connect_token = connect_token or connect_github_via_token
        self.fetch_live_stats = fetch_live_stats or fetch_live_github_stats
        self.chat_agent = chat_agent or run_github_agent_chat

    # OAuth

    def build_authorization_url(self, user_id: str) -> str:
        """Register a one-shot state for the user and return the GitHub URL."""
        client_id, _, redirect_uri = self.oauth_config()
        if not client_id:
            raise AppError("GITHUB_CLIENT_ID not configured", status_code=500)

        try:
            state = issue_state(user_id)
        except OAuthStateError as exc:
            raise AppError("OAuth state cannot be signed", status_code=500) from exc

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": OAUTH_SCOPES,
            "state": state,
        }
        return f"{GITHUB_OAUTH_URL}?{urlencode(params)}"

    def complete_oauth(self, code: str, state: str) -> None:
        """Consume the state issued by `build_authorization_url` and store tokens."""
        try:
            user_id = verify_state(state)
        except OAuthStateError as exc:
            raise AppError("OAuth state cannot be verified", status_code=500) from exc
        if not user_id:
            raise AppError("Invalid or expired OAuth state", status_code=400)

        try:
            self.connect_oauth(user_id, code)
        except GitHubConnectError as exc:
            raise AppError(str(exc), status_code=400) from exc

    def connect_with_token(self, user_id: str, access_token: str) -> Dict:
        """Verify a personal access token and store it as the user's connection."""
        token = (access_token or "").strip()
        if not token:
            raise AppError("GitHub token is required", status_code=400)

        try:
            return self.connect_token(user_id, token)
        except GitHubConnectError as exc:
            raise AppError(str(exc), status_code=400) from exc

    # Connection

    def get_status(self, user_id: str) -> Dict:
        row = self.read_status(user_id)
        if not row:
            return {"connected": False}
        return {
            "connected": True,
            "github_username": row[0],
            "avatar_url": row[1],
            "scope": row[2],
        }

    def disconnect(self, user_id: str) -> None:
        self.disconnect_user(user_id)

    # Stats

    def get_stats(self, user_id: str, force: bool = False) -> Dict:
        """Cached stats unless `force`, falling back to the cache when GitHub fails."""
        token = self.read_token(user_id)
        if not token:
            raise AppError("GitHub not connected. Go to Settings to connect.", status_code=400)

        username = self.read_username(user_id)
        if not username:
            raise AppError("GitHub username not found", status_code=400)

        cached = self.read_cached_stats(user_id, username)
        if cached and not force and _is_cache_fresh(cached):
            return _strip_internal_stats_fields(cached)

        try:
            live = self.fetch_live_stats(user_id, token, username)
        except Exception as exc:
            # Only the network call falls back to the cache. Validation used to
            # sit inside this try, so a payload GitHub shaped differently was
            # reported as a fetch failure and silently served stale data
            # (NUMA-142 P6, PLAN 7).
            self.log.warning("Live GitHub stats fetch failed: %s", exc)
            if cached:
                return _strip_internal_stats_fields(cached)
            raise AppError(
                "GitHub took too long to respond. Try again in a moment.",
                status_code=504,
                public=True,
            ) from exc

        try:
            return GitHubUserStats(**live).model_dump()
        except Exception as exc:
            # An upstream fault, not a fetch failure, and not an unhandled 500:
            # the router maps only AppError, so a raw ValidationError escaped the
            # NUMA-138 envelope entirely (NUMA-142 P6 review).
            self.log.warning("GitHub returned a payload we could not read: %s", exc)
            raise AppError(
                "GitHub returned an unexpected response. Try again in a moment.",
                status_code=502,
                public=True,
            ) from exc

    # Chat

    def chat(self, query: str, history: List[dict], user_id: Optional[str]) -> Dict:
        return self.chat_agent(query=query, history=history, user_id=user_id)


github_service = GitHubService()
