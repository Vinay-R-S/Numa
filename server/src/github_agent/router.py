"""
GitHub Router - OAuth connect/callback + stats + chat endpoints.

Thin routing layer (NUMA-109 P3 / NUMA-117 P4, PLAN 2.1 / 16.7 / 18): OAuth
config lives in config.py, DB/vector persistence in persistence.py, GitHub API
orchestration in sync.py, the LangGraph agent in agent.py, and the orchestration
behind these routes in the `Depends`-injected `GitHubService`. Names re-exported
below preserve existing import paths.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..auth.dependencies import get_current_user
from ..core.errors import AppError, http_error_from
from .config import (  # noqa: F401  re-exported for existing import paths
    GITHUB_OAUTH_URL,
    _get_github_config,
)
from .persistence import (  # noqa: F401  re-exported for existing import paths
    _get_github_token,
    get_all_connected_github_user_ids,
)
from .schemas import (
    GitHubAuthStatus,
    GitHubChatRequest,
    GitHubChatResponse,
    GitHubConnectResponse,
    GitHubTokenConnectRequest,
    GitHubUserStats,
)
from .service import GitHubService, github_service
from .sync import (  # noqa: F401  re-exported for existing import paths
    fetch_and_store_github_stats_for_user,
)

log = logging.getLogger(__name__)

# Mounted at both /github and /api/github (main.py alias): the client proxy
# strips one /api segment, direct callers keep the old prefixed URL.
router = APIRouter(prefix="/github", tags=["github"])

# Backwards-compatible re-exports (auth.router and core.data_sync import these).
__all__ = [
    "router",
    "GITHUB_OAUTH_URL",
    "_get_github_config",
    "_get_github_token",
    "fetch_and_store_github_stats_for_user",
    "get_all_connected_github_user_ids",
]


def get_github_service() -> GitHubService:
    return github_service


def _require_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user session")
    return str(user_id)


def _http_error(exc: AppError) -> HTTPException:
    # `http_error_from`, not a bare HTTPException: it carries the raiser's
    # safe-detail decision, which the 5xx redaction otherwise flattens into
    # "Internal server error" (NUMA-142 P6 review).
    return http_error_from(exc)


@router.get("/connect", response_model=GitHubConnectResponse)
def connect_github(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    try:
        url = service.build_authorization_url(_require_user_id(current_user))
    except AppError as exc:
        raise _http_error(exc) from exc

    return GitHubConnectResponse(authorization_url=url)


@router.get("/callback")
def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    service: GitHubService = Depends(get_github_service),
):
    try:
        service.complete_oauth(code=code, state=state)
    except AppError as exc:
        raise _http_error(exc) from exc

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/settings?github=connected")


@router.post("/connect-token", response_model=GitHubAuthStatus)
def connect_github_token(
    body: GitHubTokenConnectRequest,
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    try:
        status = service.connect_with_token(_require_user_id(current_user), body.access_token)
    except AppError as exc:
        raise _http_error(exc) from exc

    return GitHubAuthStatus(**status)


@router.get("/status", response_model=GitHubAuthStatus)
def github_status(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    return GitHubAuthStatus(**service.get_status(_require_user_id(current_user)))


@router.delete("/disconnect", status_code=204)
def disconnect_github(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    service.disconnect(_require_user_id(current_user))


@router.get("/stats", response_model=GitHubUserStats)
def github_stats(
    force: bool = Query(False, description="Force a live GitHub API refresh"),
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    try:
        stats = service.get_stats(_require_user_id(current_user), force=force)
    except AppError as exc:
        raise _http_error(exc) from exc

    return GitHubUserStats(**stats)


@router.post("/chat", response_model=GitHubChatResponse)
def github_chat(
    body: GitHubChatRequest,
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    result = service.chat(
        query=body.query,
        history=[m.model_dump() for m in body.history],
        user_id=_require_user_id(current_user),
    )
    return GitHubChatResponse(**result)
