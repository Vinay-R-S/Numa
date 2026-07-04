"""
Slack Sub-Agent FastAPI Router
===============================
Thin HTTP layer (NUMA-105 P3, PLAN 16.2). Config, security, Slack Web API client,
message persistence and event handling live in sibling modules; this file only
wires routes and re-exports the public names their old import paths expect.

Endpoints
---------
POST /slack/events           - Slack Events API webhook (HMAC-verified, industry-standard)
POST /slack/chat             - Invoke Slack sub-agent (JWT-protected)
GET  /slack/messages         - Fetch paginated messages (JWT-protected)
GET  /slack/channels         - List tracked channels (JWT-protected)
GET  /slack/status           - Check Slack connection status (JWT-protected)
GET  /slack/connect          - Initiate Slack OAuth flow
GET  /slack/callback         - OAuth callback; saves token to slack_auth table

Security
--------
- /slack/events uses HMAC-SHA256 signature verification (industry standard)
  as documented at https://api.slack.com/authentication/verifying-requests-from-slack
- All other endpoints require a valid NUMA JWT via Depends(get_current_user)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..auth.dependencies import get_current_user
from .repository import slack_repository
from .schemas import (
    SlackChatRequest,
    SlackChatResponse,
    SlackChannelOut,
    SlackMessageOut,
    SlackSendMessageRequest,
    SlackSendMessageResponse,
    SlackStatusOut,
    SlackSyncOut,
)
from .service import run_slack_agent_chat
from .qdrant_store import purge_old_messages
from .config import (
    _bot_token,
    _build_slack_authorization_url,
    _client_id,
    _client_secret,
    _redirect_uri,
    _frontend_url,
)
from .client import _resolve_slack_user_name
from .persistence import _upsert_slack_auth, get_all_connected_slack_user_ids  # noqa: F401  re-exported
from .events import fetch_latest_slack_for_user, handle_slack_events
from .errors import (
    _is_transient_dependency_error,
    _temporary_unavailable_detail,
    _log_dependency_exception,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

_last_channel_backfill = 0.0


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
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result  = run_slack_agent_chat(
        query=request.query,
        history=[m.model_dump() for m in request.history],
        user_id=user_id,
        model=request.model,
    )
    return SlackChatResponse(**result)


# ── Sync ───────────────────────────────────────────────────────────────────

@router.post("/sync", response_model=SlackSyncOut, summary="Sync Slack history for the current user")
def sync_slack(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = fetch_latest_slack_for_user(user_id)
    return SlackSyncOut(**result)


# ── Send Message ──────────────────────────────────────────────────────────────

@router.post("/send", response_model=SlackSendMessageResponse, summary="Send a message to a Slack channel")
def send_slack_message(
    request: SlackSendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        row = slack_repository.send_tokens_for_user(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    if not row:
        raise HTTPException(status_code=400, detail="Slack not connected")

    access_token, bot_token = row
    token = (bot_token or access_token or _bot_token() or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="No Slack token available")

    try:
        import httpx as _httpx
        with _httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "channel": request.channel_id,
                    "text": request.text,
                    **({"thread_ts": request.thread_ts} if request.thread_ts else {}),
                },
            )
        data = resp.json()
        if not data.get("ok"):
            return SlackSendMessageResponse(ok=False, error=data.get("error", "Unknown error"))
        return SlackSendMessageResponse(ok=True, ts=data.get("ts"))
    except Exception as exc:
        return SlackSendMessageResponse(ok=False, error=str(exc))


# ── 3. Messages ───────────────────────────────────────────────────────────────

@router.get("/messages", response_model=list[SlackMessageOut], summary="List recent Slack messages")
def get_slack_messages(
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    limit:   int            = Query(50,  ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    global _last_channel_backfill
    try:
        import time as _time
        if _time.time() - _last_channel_backfill > 60:
            slack_repository.backfill_channel_names(user_id)
            _last_channel_backfill = _time.time()
        msgs = slack_repository.list_messages(user_id, channel, limit)
        return [
            SlackMessageOut(
                id=str(m["id"]),
                user_id=str(m["user_id"]) if m.get("user_id") else None,
                slack_user_id=m["slack_user_id"],
                sender_name=_resolve_slack_user_name(
                    str(m.get("slack_team_id") or ""),
                    str(m.get("slack_user_id") or ""),
                    m.get("raw_payload"),
                ),
                slack_channel_id=m["slack_channel_id"],
                channel_name=m.get("channel_name"),
                text=m.get("text"),
                ts=m["ts"],
                thread_ts=m.get("thread_ts"),
                message_type=m.get("message_type", "message"),
                created_at=m.get("created_at"),
            )
            for m in msgs
        ]
    except Exception as exc:
        log.error("get_slack_messages failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


# ── 4. Channels ───────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[SlackChannelOut], summary="List tracked Slack channels")
def get_slack_channels(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    team_id = None
    try:
        auth_row = slack_repository.team_id_for_user(user_id)
        if not auth_row:
            return []
        team_id = auth_row[0]
        chs = slack_repository.channels_for_team(team_id)
    except Exception as exc:
        log.error("get_slack_channels failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch channels")

    if not chs and team_id:
        sync_result = fetch_latest_slack_for_user(user_id)
        if not sync_result.get("ok"):
            detail = sync_result.get("detail") or "Slack channel sync failed"
            raise HTTPException(status_code=502, detail=f"Slack sync failed: {detail}")

        try:
            chs = slack_repository.channels_for_team(team_id)
        except Exception as exc:
            log.error("get_slack_channels post-sync fetch failed: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to fetch synced channels")

    return [
        SlackChannelOut(
            id=str(c["id"]),
            slack_id=c["slack_id"],
            name=c.get("name"),
            team_id=c["team_id"],
            is_private=c.get("is_private", False),
            created_at=c.get("created_at"),
        )
        for c in chs
    ]


# ── 5. Status ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SlackStatusOut, summary="Check Slack connection status")
def get_slack_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        row = slack_repository.status_for_user(user_id)
        if row:
            return SlackStatusOut(
                connected=True,
                slack_user_id=row[0],
                slack_team_id=row[1],
                team_name=row[2],
                bot_configured=bool(_bot_token() or row[3]),
            )
        return SlackStatusOut(connected=False, bot_configured=bool(_bot_token()))
    except Exception as exc:
        log.error("get_slack_status failed: %s", exc)
        return SlackStatusOut(connected=False)


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
    cid    = _client_id()
    csecret = _client_secret()
    if not cid or not csecret:
        raise HTTPException(status_code=503, detail="Slack OAuth not fully configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id":     cid,
                "client_secret": csecret,
                "code":          code,
                "redirect_uri":  _redirect_uri(),
            },
        )
    data = resp.json()

    if not data.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack OAuth error: {data.get('error')}")

    authed_user  = data.get("authed_user", {})
    team         = data.get("team", {})
    slack_user_id = authed_user.get("id", "")
    slack_team_id = team.get("id", "")
    bot_token_val = data.get("access_token", "")  # bot token is at root level
    user_token_val = authed_user.get("access_token", "")
    access_token = user_token_val or bot_token_val
    team_name = team.get("name")

    # state = NUMA user_id (set during /connect)
    user_id = state.strip() if state.strip() else None

    if user_id and access_token:
        _upsert_slack_auth(
            user_id=user_id,
            slack_user_id=slack_user_id,
            slack_team_id=slack_team_id,
            access_token=access_token,
            bot_token=bot_token_val or None,
            team_name=team_name,
            authed_user_obj=authed_user,
        )
        try:
            await asyncio.to_thread(fetch_latest_slack_for_user, user_id)
        except Exception as exc:
            log.warning("Slack initial sync after OAuth failed: %s", exc)

    # Redirect to Slack page in the frontend
    return RedirectResponse(url=f"{_frontend_url()}/slack?connected=1", status_code=302)


# ── 8. Manual purge endpoint (admin / scheduler) ──────────────────────────────

@router.post("/internal/purge-old-messages",
             include_in_schema=False,
             summary="Purge Slack messages older than 7 days from Qdrant")
def purge_old_slack_messages():
    """Called by the APScheduler nightly job. Also deletes old DB rows."""
    # 1. Qdrant purge
    purge_old_messages()

    # 2. PostgreSQL purge
    db_ok = True
    message = "Old Slack data purged (7-day window)"
    try:
        deleted = slack_repository.purge_old_messages()
        log.info("Purged %d slack_messages rows older than 7 days", deleted)
    except Exception as exc:
        db_ok = False
        _log_dependency_exception("DB purge failed: %s", exc)
        message = _temporary_unavailable_detail("Slack database") if _is_transient_dependency_error(exc) else str(exc)

    return {"ok": db_ok, "message": message}
