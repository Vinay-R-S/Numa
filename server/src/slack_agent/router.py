"""
Slack Sub-Agent FastAPI Router
===============================
Thin HTTP layer (NUMA-105 P3 / NUMA-115 P4, PLAN 2.1 / 16.2 / 18). Config,
security, Slack Web API client, message persistence, event handling, OAuth and
the feature service live in sibling modules; this file parses requests,
delegates through a `Depends`-injected `SlackService`, maps errors to HTTP, and
re-exports the public names their old import paths expect.

Endpoints
---------
POST /slack/events           - Slack Events API webhook (HMAC-verified, industry-standard)
POST /slack/chat             - Invoke Slack sub-agent (JWT-protected)
POST /slack/sync             - Sync the last 7 days of history (JWT-protected)
POST /slack/send             - Post a message to a channel (JWT-protected)
GET  /slack/messages         - Fetch paginated messages (JWT-protected)
GET  /slack/channels         - List tracked channels (JWT-protected)
GET  /slack/status           - Check Slack connection status (JWT-protected)
GET  /slack/connect          - Initiate Slack OAuth flow
GET  /slack/connect-url      - Return the Slack OAuth authorization URL
GET  /slack/callback         - OAuth callback; saves token to slack_auth table
POST /slack/internal/purge-old-messages - Manual purge of old messages (admin-only)

Security
--------
- /slack/events uses HMAC-SHA256 signature verification (industry standard)
  as documented at https://api.slack.com/authentication/verifying-requests-from-slack.
  It fails closed (NUMA-129): an unsigned, stale or unverifiable request is
  refused, and a missing SLACK_SIGNING_SECRET fails the boot when Slack is
  configured rather than leaving the webhook open.
- /slack/internal/purge-old-messages deletes every user's Slack rows and
  vectors outside the retention window, so it takes Depends(require_admin)
  (NUMA-130). Being hidden from the schema was never access control.
- All other endpoints require a valid NUMA JWT via Depends(get_current_user)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..auth.dependencies import get_current_user, require_admin
from ..core.errors import AppError
from .client import _resolve_slack_user_name  # noqa: F401  re-exported
from .config import (  # noqa: F401  re-exported
    _bot_token,
    _build_slack_authorization_url,
    _client_id,
    _client_secret,
    _frontend_url,
    _redirect_uri,
)
from .events import fetch_latest_slack_for_user, handle_slack_events  # noqa: F401  re-exported
from .oauth import complete_oauth_connection
from .persistence import _upsert_slack_auth, get_all_connected_slack_user_ids  # noqa: F401  re-exported
from .schemas import (
    SlackChannelOut,
    SlackChatRequest,
    SlackChatResponse,
    SlackMessageOut,
    SlackSendMessageRequest,
    SlackSendMessageResponse,
    SlackStatusOut,
    SlackSyncOut,
)
from .service import SlackService, run_slack_agent_chat, slack_service  # noqa: F401  re-exported

log = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


def get_slack_service() -> SlackService:
    return slack_service


def _require_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    return str(user_id)


def _http_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


# ── 1. Slack Events API (webhook - HMAC verified) ─────────────────────────────

@router.post("/events", include_in_schema=True,
             summary="Slack Events API webhook (HMAC-verified)")
async def slack_events(request: Request):
    return await handle_slack_events(request)


# ── 2. Chat ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=SlackChatResponse, summary="Chat with the Slack sub-agent")
def slack_chat(
    request: SlackChatRequest,
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result = service.chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=user_id,
        model=request.model,
    )
    return SlackChatResponse(**result)


# ── Sync ───────────────────────────────────────────────────────────────────

@router.post("/sync", response_model=SlackSyncOut, summary="Sync Slack history for the current user")
def sync_slack(
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    return SlackSyncOut(**service.sync_user(_require_user_id(current_user)))


# ── Send Message ──────────────────────────────────────────────────────────────

@router.post("/send", response_model=SlackSendMessageResponse, summary="Send a message to a Slack channel")
def send_slack_message(
    request: SlackSendMessageRequest,
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    try:
        result = service.send_message(
            user_id=_require_user_id(current_user),
            channel_id=request.channel_id,
            text=request.text,
            thread_ts=request.thread_ts,
        )
    except AppError as exc:
        raise _http_error(exc) from exc

    return SlackSendMessageResponse(**result)


# ── 3. Messages ───────────────────────────────────────────────────────────────

@router.get("/messages", response_model=list[SlackMessageOut], summary="List recent Slack messages")
def get_slack_messages(
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    try:
        messages = service.list_messages(_require_user_id(current_user), channel, limit)
    except AppError as exc:
        raise _http_error(exc) from exc

    return [SlackMessageOut(**m) for m in messages]


# ── 4. Channels ───────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[SlackChannelOut], summary="List tracked Slack channels")
def get_slack_channels(
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    try:
        channels = service.list_channels(_require_user_id(current_user))
    except AppError as exc:
        raise _http_error(exc) from exc

    return [SlackChannelOut(**c) for c in channels]


# ── 5. Status ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SlackStatusOut, summary="Check Slack connection status")
def get_slack_status(
    current_user: dict = Depends(get_current_user),
    service: SlackService = Depends(get_slack_service),
):
    return SlackStatusOut(**service.get_status(_require_user_id(current_user)))


# ── 6. OAuth Connect ──────────────────────────────────────────────────────────

@router.get("/connect", summary="Initiate Slack OAuth flow")
def slack_connect(current_user: dict = Depends(get_current_user)):
    return RedirectResponse(
        url=_build_slack_authorization_url(current_user.get("sub", "")),
        status_code=302,
    )


@router.get("/connect-url", summary="Get Slack OAuth authorization URL")
def slack_connect_url(current_user: dict = Depends(get_current_user)):
    return {
        "authorization_url": _build_slack_authorization_url(current_user.get("sub", "")),
    }


# ── 7. OAuth Callback ─────────────────────────────────────────────────────────

@router.get("/callback", summary="Slack OAuth callback")
async def slack_callback(code: str = Query(...), state: str = Query("")):
    try:
        redirect_url = await complete_oauth_connection(code, state)
    except AppError as exc:
        raise _http_error(exc) from exc

    return RedirectResponse(url=redirect_url, status_code=302)


# ── 8. Manual purge endpoint (admin-only) ─────────────────────────────────────

@router.post("/internal/purge-old-messages",
             include_in_schema=False,
             summary="Purge Slack messages older than 7 days (admin-only)")
def purge_old_slack_messages(
    current_user: dict = Depends(require_admin),
    service: SlackService = Depends(get_slack_service),
):
    """Operator-triggered purge, admin-only (NUMA-130 P6, PLAN 8).

    The scheduled purge does not come through here: `core/data_sync.py` calls
    `slack_service.purge_old_messages()` in-process. This route is the manual
    trigger, and it drops every user's Slack vectors and rows outside the 7-day
    window, so it takes the same gate as the other server-wide operations.
    """
    return service.purge_old_messages()
