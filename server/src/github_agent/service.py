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

import secrets
from typing import Callable, Dict, List, MutableMapping, Optional
from urllib.parse import urlencode

from ..core.base import BaseService
from ..core.errors import AppError
from .agent import (  # noqa: F401  re-exported for existing import paths
    GITHUB_AGENT_SYSTEM_PROMPT,
    GitHubAgentState,
    run_github_agent_chat,
)
from .config import GITHUB_OAUTH_URL, _get_github_config, _oauth_states
from .persistence import (
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
OAUTH_STATE_BYTES = 32


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
        oauth_states: Optional[MutableMapping[str, str]] = None,
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
        self.oauth_states = _oauth_states if oauth_states is None else oauth_states
        self.connect_oauth = connect_oauth or connect_github_via_oauth
        self.connect_token = connect_token or connect_github_via_token
        self.fetch_live_stats = fetch_live_stats or fetch_live_github_stats
        self.chat_agent = chat_agent or run_github_agent_chat

    # ── OAuth ────────────────────────────────────────────────────────────────

    def build_authorization_url(self, user_id: str) -> str:
        """Register a one-shot state for the user and return the GitHub URL."""
        client_id, _, redirect_uri = self.oauth_config()
        if not client_id:
            raise AppError("GITHUB_CLIENT_ID not configured", status_code=500)

        state = secrets.token_urlsafe(OAUTH_STATE_BYTES)
        self.oauth_states[state] = user_id

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": OAUTH_SCOPES,
            "state": state,
        }
        return f"{GITHUB_OAUTH_URL}?{urlencode(params)}"

    def complete_oauth(self, code: str, state: str) -> None:
        """Consume the state issued by `build_authorization_url` and store tokens."""
        user_id = self.oauth_states.pop(state, None)
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

    # ── Connection ───────────────────────────────────────────────────────────

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

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self, user_id: str, force: bool = False) -> Dict:
        """Cached stats unless `force`, falling back to the cache when GitHub fails."""
        token = self.read_token(user_id)
        if not token:
            raise AppError("GitHub not connected. Go to Settings to connect.", status_code=400)

        username = self.read_username(user_id)
        if not username:
            raise AppError("GitHub username not found", status_code=400)

        cached = self.read_cached_stats(user_id, username)
        if cached and not force:
            return _strip_internal_stats_fields(cached)

        try:
            # Validated here, not in the route: a live payload GitHub shaped
            # differently (a null repo count, say) used to fall through to the
            # cache rather than surface as a 500, because the old route built the
            # response model inside this same try.
            return GitHubUserStats(**self.fetch_live_stats(user_id, token, username)).model_dump()
        except Exception as exc:
            self.log.warning("Live GitHub stats fetch failed: %s", exc)
            if cached:
                return _strip_internal_stats_fields(cached)
            raise AppError(
                "GitHub took too long to respond. Try again in a moment.",
                status_code=504,
            ) from exc

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat(self, query: str, history: List[dict], user_id: Optional[str]) -> Dict:
        return self.chat_agent(query=query, history=history, user_id=user_id)


github_service = GitHubService()
