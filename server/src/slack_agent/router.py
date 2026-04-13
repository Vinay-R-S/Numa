"""
Slack Sub-Agent FastAPI Router
===============================
Endpoints
---------
POST /slack/events           — Slack Events API webhook (HMAC-verified, industry-standard)
POST /slack/chat             — Invoke Slack sub-agent (JWT-protected)
GET  /slack/messages         — Fetch paginated messages (JWT-protected)
GET  /slack/channels         — List tracked channels (JWT-protected)
GET  /slack/status           — Check Slack connection status (JWT-protected)
GET  /slack/connect          — Initiate Slack OAuth flow
GET  /slack/callback         — OAuth callback; saves token to slack_auth table

Security
--------
- /slack/events uses HMAC-SHA256 signature verification (industry standard)
  as documented at https://api.slack.com/authentication/verifying-requests-from-slack
- All other endpoints require a valid NUMA JWT via Depends(get_current_user)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from .schemas import (
    SlackChatRequest,
    SlackChatResponse,
    SlackChannelOut,
    SlackMessageOut,
    SlackStatusOut,
)
from .service import run_slack_agent_chat
from .qdrant_store import ingest_message, purge_old_messages

log = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# ── Config ─────────────────────────────────────────────────────────────────────

def _signing_secret() -> str:
    return os.getenv("SLACK_SIGNING_SECRET", "").strip()

def _client_id() -> str:
    return os.getenv("SLACK_CLIENT_ID", "").strip()

def _client_secret() -> str:
    return os.getenv("SLACK_CLIENT_SECRET", "").strip()

def _redirect_uri() -> str:
    return os.getenv("SLACK_REDIRECT_URI", "http://localhost:8000/slack/callback").strip()

def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").strip()

def _bot_token() -> str:
    return os.getenv("SLACK_BOT_TOKEN", "").strip()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _row_to_dict(row, description) -> dict:
    return {col.name: val for col, val in zip(description, row)}


def _get_or_create_channel(slack_id: str, name: Optional[str], team_id: str) -> Optional[str]:
    """Return the UUID of a slack_channels row, creating it if necessary."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM public.slack_channels WHERE slack_id = %s LIMIT 1",
            (slack_id,),
        )
        row = cur.fetchone()
        if row:
            cur.close()
            return str(row[0])
        cur.execute(
            "INSERT INTO public.slack_channels (slack_id, name, team_id) VALUES (%s, %s, %s) RETURNING id",
            (slack_id, name, team_id),
        )
        new_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        return new_id
    except Exception as exc:
        log.warning("_get_or_create_channel failed: %s", exc)
        conn.rollback()
        return None
    finally:
        conn.close()


def _resolve_user_id_by_slack(slack_user_id: str) -> Optional[str]:
    """Return NUMA user_id for a given Slack user id (from slack_auth table)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM public.slack_auth WHERE slack_user_id = %s LIMIT 1",
            (slack_user_id,),
        )
        row = cur.fetchone()
        cur.close()
        return str(row[0]) if row else None
    except Exception as exc:
        log.warning("_resolve_user_id_by_slack failed: %s", exc)
        return None
    finally:
        conn.close()


def _save_slack_message(event: dict, channel_name: Optional[str] = None):
    """Persist a Slack message/event to slack_messages and ingest into Qdrant."""
    slack_user_id = event.get("user", "")
    slack_team_id = event.get("team", "") or ""
    ts            = event.get("ts", "")
    text          = event.get("text", "") or ""
    slack_chan_id = event.get("channel", "")

    if not slack_user_id or not ts:
        return

    user_id    = _resolve_user_id_by_slack(slack_user_id)
    channel_uuid = _get_or_create_channel(slack_chan_id, channel_name, slack_team_id) if slack_chan_id else None

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.slack_messages
                (user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id,
                 channel_name, text, ts, thread_ts, message_type, raw_payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts) DO NOTHING
            """,
            (
                user_id,
                slack_user_id,
                slack_team_id,
                channel_uuid,
                slack_chan_id,
                channel_name,
                text,
                ts,
                event.get("thread_ts"),
                "message",
                json.dumps(event),
            ),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("_save_slack_message DB insert failed: %s", exc)
        conn.rollback()
        return
    finally:
        conn.close()

    # Ingest into Qdrant (best-effort)
    if text.strip() and user_id:
        try:
            ingest_message(
                user_id=user_id,
                slack_user_id=slack_user_id,
                slack_channel_id=slack_chan_id,
                channel_name=channel_name or slack_chan_id,
                text=text,
                ts=ts,
                thread_ts=event.get("thread_ts"),
                message_type="message",
            )
        except Exception as exc:
            log.warning("Qdrant ingest failed: %s", exc)


def _upsert_slack_auth(
    user_id: str,
    slack_user_id: str,
    slack_team_id: str,
    access_token: str,
    bot_token: Optional[str],
    team_name: Optional[str],
    authed_user_obj: Optional[dict],
):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.slack_auth
                (user_id, slack_user_id, slack_team_id, access_token, bot_token, team_name, authed_user_obj)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                slack_user_id   = EXCLUDED.slack_user_id,
                slack_team_id   = EXCLUDED.slack_team_id,
                access_token    = EXCLUDED.access_token,
                bot_token       = EXCLUDED.bot_token,
                team_name       = EXCLUDED.team_name,
                authed_user_obj = EXCLUDED.authed_user_obj,
                updated_at      = NOW()
            """,
            (
                user_id,
                slack_user_id,
                slack_team_id,
                access_token,
                bot_token,
                team_name,
                json.dumps(authed_user_obj) if authed_user_obj else None,
            ),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("_upsert_slack_auth failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()


# ── HMAC Signature Verification ───────────────────────────────────────────────

def _verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack's HMAC-SHA256 request signature (industry-standard security)."""
    secret = _signing_secret()
    if not secret:
        # If signing secret is not configured, skip verification (dev mode)
        log.warning("SLACK_SIGNING_SECRET not configured — skipping signature check!")
        return True

    try:
        ts_int = int(timestamp)
        if abs(time.time() - ts_int) > 300:
            log.warning("Slack event timestamp too old: %s", timestamp)
            return False
        base_string = f"v0:{timestamp}:{request_body.decode('utf-8')}"
        computed    = "v0=" + hmac.new(
            secret.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception as exc:
        log.warning("Signature verification error: %s", exc)
        return False


# ── Resolve channel name via Slack API ────────────────────────────────────────

def _resolve_channel_name(channel_id: str) -> Optional[str]:
    bot = _bot_token()
    if not bot:
        return None
    try:
        from slack_sdk import WebClient  # type: ignore
        wc   = WebClient(token=bot)
        info = wc.conversations_info(channel=channel_id)
        return info["channel"].get("name")
    except Exception:
        return None


# ── Routes ─────────────────────────────────────────────────────────────────────

# ── 1. Slack Events API (webhook – HMAC verified) ─────────────────────────────

@router.post("/events", include_in_schema=True,
             summary="Slack Events API webhook (HMAC-verified)")
async def slack_events(request: Request):
    """
    Receives Slack events via the Events API.
    Uses HMAC-SHA256 signature verification to confirm authenticity.
    Responds within 3 seconds as required by Slack's API contract.
    """
    body_bytes = await request.body()

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(body_bytes, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # ── URL verification challenge (one-time, during app setup) ──────────────
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge", "")})

    # ── Handle event callbacks ─────────────────────────────────────────────────
    event = payload.get("event", {})
    event_type = event.get("type", "")

    if event_type == "message":
        # Skip bot messages, edits, and deletions
        if event.get("bot_id") or event.get("subtype") in ("message_changed", "message_deleted", "bot_message"):
            return Response(status_code=200)

        # Propagate team_id from outer envelope if missing in event
        if not event.get("team"):
            event["team"] = payload.get("team_id", "")

        # Try to resolve channel name (best-effort)
        channel_id   = event.get("channel", "")
        channel_name = _resolve_channel_name(channel_id) if channel_id else None

        # Persist + ingest
        _save_slack_message(event, channel_name)

        # Run task-extraction agent for @mentions or broadcasts
        text = event.get("text", "")
        if any(m in text for m in ("<@", "<!channel>", "<!here>", "<!everyone>")):
            _run_agent_task_extraction(text, event.get("ts"), payload.get("team_id"))

    return Response(status_code=200)


def _run_agent_task_extraction(text: str, ts: Optional[str], team_id: Optional[str]):
    """Background call: extract action items from @mentioned messages."""
    try:
        import re
        mentioned_slack_ids = re.findall(r"<@([A-Z0-9]+)>", text)
        if not mentioned_slack_ids:
            return
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, slack_user_id FROM public.slack_auth WHERE slack_user_id = ANY(%s)",
                (mentioned_slack_ids,),
            )
            rows = cur.fetchall()
            cur.close()
        finally:
            conn.close()

        for user_id_row, _slack_id in rows:
            user_id = str(user_id_row)
            _extract_and_create_task(text, ts, user_id)
    except Exception as exc:
        log.warning("_run_agent_task_extraction error: %s", exc)


def _extract_and_create_task(text: str, ts: Optional[str], user_id: str):
    """Use Groq LLM to detect if text is actionable and create a task."""
    try:
        from datetime import date
        from langchain_groq import ChatGroq  # type: ignore
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import PydanticOutputParser  # type: ignore
        from pydantic import BaseModel

        class TaskExtraction(BaseModel):
            is_actionable: bool
            task_title: Optional[str] = None
            task_priority: str = "medium"
            task_due: Optional[str] = None

        parser = PydanticOutputParser(pydantic_object=TaskExtraction)
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are NUMA. Decide if the Slack message requires action.\n"
                "Today: {today}\n"
                "{format_instructions}"
            )),
            ("human", "{text}"),
        ])
        llm   = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        chain = prompt | llm | parser
        result: TaskExtraction = chain.invoke({
            "text": text,
            "today": date.today().isoformat(),
            "format_instructions": parser.get_format_instructions(),
        })
        if result.is_actionable and result.task_title:
            from .service import _insert_task_from_slack
            _insert_task_from_slack(
                user_id=user_id,
                title=result.task_title,
                priority=result.task_priority if result.task_priority in {"low","medium","high","urgent"} else "medium",
                due_date=result.task_due,
                slack_ts=ts,
            )
    except Exception as exc:
        log.warning("_extract_and_create_task failed: %s", exc)


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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        if channel:
            cur.execute(
                """
                SELECT id, user_id, slack_user_id, slack_channel_id, channel_name,
                       text, ts, thread_ts, message_type, created_at
                FROM public.slack_messages
                WHERE user_id = %s
                  AND created_at > NOW() - INTERVAL '7 days'
                  AND LOWER(channel_name) = LOWER(%s)
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, channel.lstrip("#"), limit),
            )
        else:
            cur.execute(
                """
                SELECT id, user_id, slack_user_id, slack_channel_id, channel_name,
                       text, ts, thread_ts, message_type, created_at
                FROM public.slack_messages
                WHERE user_id = %s
                  AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
        rows = cur.fetchall()
        msgs = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return [
            SlackMessageOut(
                id=str(m["id"]),
                user_id=str(m["user_id"]) if m.get("user_id") else None,
                slack_user_id=m["slack_user_id"],
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
    finally:
        conn.close()


# ── 4. Channels ───────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[SlackChannelOut], summary="List tracked Slack channels")
def get_slack_channels(current_user: dict = Depends(get_current_user)):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT sc.id, sc.slack_id, sc.name, sc.team_id, sc.is_private, sc.created_at
            FROM public.slack_channels sc
            INNER JOIN public.slack_messages sm ON sm.channel_id = sc.id
            WHERE sm.created_at > NOW() - INTERVAL '7 days'
            ORDER BY sc.name ASC
            """,
        )
        rows = cur.fetchall()
        chs  = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
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
    except Exception as exc:
        log.error("get_slack_channels failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch channels")
    finally:
        conn.close()


# ── 5. Status ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SlackStatusOut, summary="Check Slack connection status")
def get_slack_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT slack_user_id, slack_team_id, team_name FROM public.slack_auth WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()

        if row:
            return SlackStatusOut(
                connected=True,
                slack_user_id=row[0],
                slack_team_id=row[1],
                team_name=row[2],
                bot_configured=bool(_bot_token()),
            )
        return SlackStatusOut(connected=False, bot_configured=bool(_bot_token()))
    except Exception as exc:
        log.error("get_slack_status failed: %s", exc)
        return SlackStatusOut(connected=False)
    finally:
        conn.close()


# ── 6. OAuth Connect ──────────────────────────────────────────────────────────

@router.get("/connect", summary="Initiate Slack OAuth flow")
def slack_connect(current_user: dict = Depends(get_current_user)):
    cid = _client_id()
    if not cid:
        raise HTTPException(status_code=503, detail="SLACK_CLIENT_ID not configured")

    params = urlencode({
        "client_id":    cid,
        "scope":        "channels:history,channels:read,chat:write,users:read,team:read",
        "user_scope":   "channels:history,chat:write",
        "redirect_uri": _redirect_uri(),
        "state":        current_user.get("sub", ""),
    })
    return RedirectResponse(url=f"https://slack.com/oauth/v2/authorize?{params}", status_code=302)


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
    access_token  = authed_user.get("access_token") or data.get("access_token", "")
    bot_token_val = data.get("access_token", "")  # bot token is at root level
    team_name     = team.get("name")

    # state = NUMA user_id (set during /connect)
    user_id = state.strip() if state.strip() else None

    if user_id and access_token:
        _upsert_slack_auth(
            user_id=user_id,
            slack_user_id=slack_user_id,
            slack_team_id=slack_team_id,
            access_token=access_token,
            bot_token=bot_token_val if bot_token_val != access_token else None,
            team_name=team_name,
            authed_user_obj=authed_user,
        )

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
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM public.slack_messages WHERE created_at < NOW() - INTERVAL '7 days'"
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        log.info("Purged %d slack_messages rows older than 7 days", deleted)
    except Exception as exc:
        log.warning("DB purge failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()

    return {"ok": True, "message": "Old Slack data purged (7-day window)"}
