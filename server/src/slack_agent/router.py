"""
Slack Sub-Agent FastAPI Router
===============================
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

import hashlib
import hmac
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
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
    SlackSendMessageRequest,
    SlackSendMessageResponse,
    SlackStatusOut,
    SlackSyncOut,
)
from .service import run_slack_agent_chat
from .qdrant_store import delete_message, ingest_message, purge_old_messages

log = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

_last_channel_backfill = 0.0
_slack_user_name_cache: dict[str, tuple[float, str]] = {}

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


DEFAULT_SLACK_BOT_SCOPES = [
    "app_mentions:read",
    "channels:history",
    "channels:join",
    "channels:manage",
    "channels:read",
    "channels:write.invites",
    "chat:write",
    "commands",
    "files:read",
    "files:write",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    "reactions:read",
    "reactions:write",
    "search:read.files",
    "search:read.public",
    "search:read.users",
    "team:read",
    "users:read",
    "users:read.email",
]


def _oauth_scopes() -> str:
    configured = os.getenv("SLACK_BOT_SCOPES", "").strip()
    scopes = [s.strip() for s in configured.split(",") if s.strip()] if configured else []
    for scope in DEFAULT_SLACK_BOT_SCOPES:
        if scope not in scopes:
            scopes.append(scope)
    return ",".join(scopes)


def _build_slack_authorization_url(user_id: str) -> str:
    cid = _client_id()
    if not cid:
        raise HTTPException(status_code=503, detail="SLACK_CLIENT_ID not configured")

    params = urlencode({
        "client_id":    cid,
        "scope":        _oauth_scopes(),
        "redirect_uri": _redirect_uri(),
        "state":        user_id,
    })
    return f"https://slack.com/oauth/v2/authorize?{params}"


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _row_to_dict(row, description) -> dict:
    return {col.name: val for col, val in zip(description, row)}


def _get_or_create_channel(
    slack_id: str,
    name: Optional[str],
    team_id: str,
    is_private: bool = False,
) -> Optional[str]:
    """Return the UUID of a slack_channels row, creating it if necessary."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name FROM public.slack_channels WHERE slack_id = %s LIMIT 1",
            (slack_id,),
        )
        row = cur.fetchone()
        if row:
            channel_id, existing_name = row
            if name and (not existing_name or existing_name != name):
                cur.execute(
                    "UPDATE public.slack_channels SET name = %s, is_private = %s WHERE id = %s",
                    (name, is_private, channel_id),
                )
                conn.commit()
            elif is_private:
                cur.execute(
                    "UPDATE public.slack_channels SET is_private = %s WHERE id = %s",
                    (is_private, channel_id),
                )
                conn.commit()
            cur.close()
            return str(channel_id)
        cur.execute(
            """
            INSERT INTO public.slack_channels (slack_id, name, team_id, is_private)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (slack_id, name, team_id, is_private),
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


def _get_channel_name_from_db(slack_id: str) -> Optional[str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM public.slack_channels WHERE slack_id = %s LIMIT 1",
            (slack_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception:
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


def _user_ids_for_slack_team(team_id: str) -> list[str]:
    if not team_id:
        return []

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM public.slack_auth WHERE slack_team_id = %s",
            (team_id,),
        )
        rows = cur.fetchall() or []
        cur.close()
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as exc:
        log.warning("_user_ids_for_slack_team failed: %s", exc)
        return []
    finally:
        conn.close()


def _team_bot_token(team_id: str) -> Optional[str]:
    if not team_id:
        return None

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bot_token, access_token
            FROM public.slack_auth
            WHERE slack_team_id = %s
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (team_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return (row[0] or row[1] or "").strip() or None
    except Exception as exc:
        log.warning("_team_bot_token failed: %s", exc)
        return None
    finally:
        conn.close()


def _raw_payload_dict(raw_payload) -> dict:
    if isinstance(raw_payload, dict):
        return raw_payload
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _name_from_slack_profile(payload: dict) -> Optional[str]:
    profile = payload.get("user_profile")
    if not isinstance(profile, dict):
        profile = {}

    for value in (
        profile.get("real_name"),
        profile.get("display_name"),
        profile.get("name"),
        payload.get("username"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _resolve_slack_user_name(team_id: str, slack_user_id: str, raw_payload=None) -> Optional[str]:
    payload_name = _name_from_slack_profile(_raw_payload_dict(raw_payload))
    if payload_name:
        return payload_name

    if not team_id or not slack_user_id:
        return None

    cache_key = f"{team_id}:{slack_user_id}"
    cached = _slack_user_name_cache.get(cache_key)
    if cached and time.time() - cached[0] < 3600:
        return cached[1]

    token = _team_bot_token(team_id) or _bot_token()
    if not token:
        return None

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                "https://slack.com/api/users.info",
                headers={"Authorization": f"Bearer {token}"},
                params={"user": slack_user_id},
            )
        data = resp.json()
        if not data.get("ok"):
            return None
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
        for value in (
            profile.get("real_name"),
            profile.get("display_name"),
            user.get("real_name"),
            user.get("name"),
        ):
            if isinstance(value, str) and value.strip():
                name = value.strip()
                _slack_user_name_cache[cache_key] = (time.time(), name)
                return name
    except Exception as exc:
        log.info("Slack user name lookup skipped for %s: %s", slack_user_id, exc)

    return None


def _cache_workspace_user_names(client: httpx.Client, token: str, team_id: str) -> None:
    if not token or not team_id:
        return

    cursor = ""
    while True:
        resp = client.get(
            "https://slack.com/api/users.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": "500", **({"cursor": cursor} if cursor else {})},
        )
        data = resp.json()
        if not data.get("ok"):
            log.info("Slack users.list skipped: %s", data.get("error"))
            return

        for member in data.get("members", []):
            if not isinstance(member, dict) or member.get("deleted"):
                continue
            slack_user_id = str(member.get("id") or "").strip()
            if not slack_user_id:
                continue
            profile = member.get("profile") if isinstance(member.get("profile"), dict) else {}
            for value in (
                profile.get("real_name"),
                profile.get("display_name"),
                member.get("real_name"),
                member.get("name"),
            ):
                if isinstance(value, str) and value.strip():
                    _slack_user_name_cache[f"{team_id}:{slack_user_id}"] = (time.time(), value.strip())
                    break

        cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
        if not cursor:
            return


def _save_slack_message(event: dict, channel_name: Optional[str] = None):
    """Persist a Slack message/event to slack_messages and ingest into Qdrant."""
    slack_user_id = event.get("user", "")
    slack_team_id = event.get("team", "") or ""
    ts            = event.get("ts", "")
    text          = event.get("text", "") or ""
    slack_chan_id = event.get("channel", "")

    if not slack_user_id or not ts:
        return

    target_user_ids = _user_ids_for_slack_team(slack_team_id)
    if not target_user_ids:
        resolved = _resolve_user_id_by_slack(slack_user_id)
        target_user_ids = [resolved] if resolved else []

    if target_user_ids:
        for target_user_id in target_user_ids:
            _save_slack_message_for_user(
                user_id=target_user_id,
                event=event,
                channel_name=channel_name,
                team_id=slack_team_id,
            )
        return

    user_id = None
    resolved_channel_name = channel_name or _get_channel_name_from_db(slack_chan_id)
    channel_uuid = _get_or_create_channel(slack_chan_id, resolved_channel_name, slack_team_id) if slack_chan_id else None

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.slack_messages
                (user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id,
                 channel_name, text, ts, thread_ts, message_type, raw_payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts) DO UPDATE SET
                user_id = COALESCE(public.slack_messages.user_id, EXCLUDED.user_id),
                slack_team_id = EXCLUDED.slack_team_id,
                channel_id = COALESCE(public.slack_messages.channel_id, EXCLUDED.channel_id),
                slack_channel_id = EXCLUDED.slack_channel_id,
                channel_name = COALESCE(EXCLUDED.channel_name, public.slack_messages.channel_name),
                text = EXCLUDED.text,
                thread_ts = EXCLUDED.thread_ts,
                message_type = EXCLUDED.message_type,
                raw_payload = EXCLUDED.raw_payload
            """,
            (
                user_id,
                slack_user_id,
                slack_team_id,
                channel_uuid,
                slack_chan_id,
                resolved_channel_name,
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
                channel_name=resolved_channel_name or slack_chan_id,
                text=text,
                ts=ts,
                thread_ts=event.get("thread_ts"),
                message_type="message",
            )
        except Exception as exc:
            log.warning("Qdrant ingest failed: %s", exc)


def _delete_slack_message_by_ts(ts: str, slack_user_id: Optional[str] = None) -> None:
    if not ts:
        return

    user_id = _resolve_user_id_by_slack(slack_user_id or "") if slack_user_id else None
    if not user_id:
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM public.slack_messages WHERE ts = %s LIMIT 1",
                (ts,),
            )
            row = cur.fetchone()
            cur.close()
            user_id = str(row[0]) if row and row[0] else None
        except Exception as exc:
            log.warning("_delete_slack_message_by_ts lookup failed: %s", exc)
        finally:
            conn.close()

    conn = _get_conn()
    task_ids: list[str] = []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id FROM public.tasks WHERE external_ref = %s",
            (f"slack:{ts}",),
        )
        task_ids = [str(row[0]) for row in (cur.fetchall() or []) if row and row[0]]
        cur.execute("DELETE FROM public.slack_messages WHERE ts = %s", (ts,))
        cur.execute(
            "DELETE FROM public.tasks WHERE external_ref = %s",
            (f"slack:{ts}",),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("_delete_slack_message_by_ts DB delete failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()

    if user_id:
        delete_message(user_id=user_id, ts=ts)
        try:
            from ..tasks import service as task_service
            for task_id in task_ids:
                task_service.delete_task_snapshot(user_id, task_id)
        except Exception:
            pass


def _update_slack_message(event: dict, channel_name: Optional[str] = None) -> None:
    message = event.get("message") if isinstance(event.get("message"), dict) else event
    previous = event.get("previous_message") if isinstance(event.get("previous_message"), dict) else {}
    ts = message.get("ts") or event.get("ts") or previous.get("ts")
    text = message.get("text") or ""
    slack_user_id = message.get("user") or previous.get("user") or event.get("user") or ""
    slack_chan_id = message.get("channel") or event.get("channel") or previous.get("channel") or ""
    if not ts or not slack_user_id:
        return

    user_id = _resolve_user_id_by_slack(slack_user_id)
    if not user_id:
        return

    resolved_channel_name = channel_name or _get_channel_name_from_db(slack_chan_id)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE public.slack_messages
            SET text = %s,
                channel_name = COALESCE(%s, channel_name),
                raw_payload = %s
            WHERE ts = %s
            """,
            (text, resolved_channel_name, json.dumps(event), ts),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("_update_slack_message DB update failed: %s", exc)
        conn.rollback()
        return
    finally:
        conn.close()

    if text.strip():
        ingest_message(
            user_id=user_id,
            slack_user_id=slack_user_id,
            slack_channel_id=slack_chan_id,
            channel_name=resolved_channel_name or slack_chan_id,
            text=text,
            ts=ts,
            thread_ts=message.get("thread_ts"),
            message_type=message.get("subtype") or "message",
        )


def _save_slack_message_for_user(
    user_id: str,
    event: dict,
    channel_name: Optional[str] = None,
    team_id: Optional[str] = None,
) -> bool:
    """Persist a Slack message fetched from Web API for a connected NUMA user."""
    slack_user_id = event.get("user") or event.get("bot_id") or ""
    slack_team_id = team_id or event.get("team") or ""
    ts            = event.get("ts", "")
    text          = event.get("text", "") or ""
    slack_chan_id = event.get("channel", "")

    if not user_id or not slack_user_id or not ts or not slack_chan_id:
        return False

    resolved_channel_name = channel_name or _get_channel_name_from_db(slack_chan_id)
    channel_uuid = _get_or_create_channel(slack_chan_id, resolved_channel_name, slack_team_id) if slack_chan_id else None
    try:
        created_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except Exception:
        created_at = datetime.now(timezone.utc)

    conn = _get_conn()
    inserted = False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.slack_messages
                (user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id,
                 channel_name, text, ts, thread_ts, message_type, raw_payload, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                slack_user_id = EXCLUDED.slack_user_id,
                slack_team_id = EXCLUDED.slack_team_id,
                channel_id = COALESCE(EXCLUDED.channel_id, public.slack_messages.channel_id),
                slack_channel_id = EXCLUDED.slack_channel_id,
                channel_name = COALESCE(EXCLUDED.channel_name, public.slack_messages.channel_name),
                text = EXCLUDED.text,
                thread_ts = EXCLUDED.thread_ts,
                message_type = EXCLUDED.message_type,
                raw_payload = EXCLUDED.raw_payload,
                created_at = EXCLUDED.created_at
            """,
            (
                user_id,
                slack_user_id,
                slack_team_id,
                channel_uuid,
                slack_chan_id,
                resolved_channel_name,
                text,
                ts,
                event.get("thread_ts"),
                event.get("subtype") or "message",
                json.dumps(event),
                created_at,
            ),
        )
        inserted = cur.rowcount > 0
        conn.commit()
        cur.close()
    except Exception as exc:
        log.warning("_save_slack_message_for_user DB insert failed: %s", exc)
        conn.rollback()
        return False
    finally:
        conn.close()

    if text.strip():
        try:
            ingest_message(
                user_id=user_id,
                slack_user_id=slack_user_id,
                slack_channel_id=slack_chan_id,
                channel_name=resolved_channel_name or slack_chan_id,
                text=text,
                ts=ts,
                thread_ts=event.get("thread_ts"),
                message_type=event.get("subtype") or "message",
            )
        except Exception as exc:
            log.warning("Qdrant ingest failed: %s", exc)

    return inserted


def get_all_connected_slack_user_ids() -> list[str]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM public.slack_auth")
        rows = cur.fetchall() or []
        cur.close()
        return [str(row[0]) for row in rows]
    except Exception as exc:
        log.warning("get_all_connected_slack_user_ids failed: %s", exc)
        return []
    finally:
        conn.close()


def fetch_latest_slack_for_user(user_id: str) -> dict:
    """Fetch the last 7 days of Slack channel messages for one connected user."""
    if not user_id:
        return {"ok": False, "fetched": 0, "channels": 0, "detail": "Missing user id"}

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT access_token, bot_token, slack_team_id
            FROM public.slack_auth
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
    except Exception as exc:
        log.warning("fetch_latest_slack_for_user auth lookup failed: %s", exc)
        return {"ok": False, "fetched": 0, "channels": 0, "detail": str(exc)}
    finally:
        conn.close()

    if not row:
        return {"ok": True, "fetched": 0, "channels": 0, "detail": "Slack not connected"}

    access_token, bot_token, team_id = row
    token = (bot_token or access_token or _bot_token() or "").strip()
    if not token:
        return {"ok": False, "fetched": 0, "channels": 0, "detail": "Slack token not configured"}

    oldest = str((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())
    headers = {"Authorization": f"Bearer {token}"}
    fetched = 0
    channels_seen = 0
    channels_synced = 0

    try:
        with httpx.Client(timeout=20.0) as client:
            _cache_workspace_user_names(client, token, team_id)

            cursor = ""
            channels: list[dict] = []
            while True:
                channels_resp = client.get(
                    "https://slack.com/api/conversations.list",
                    headers=headers,
                    params={
                        "types": "public_channel,private_channel",
                        "exclude_archived": "true",
                        "limit": "500",
                        **({"cursor": cursor} if cursor else {}),
                    },
                )
                channels_data = channels_resp.json()
                if not channels_data.get("ok"):
                    return {
                        "ok": False,
                        "fetched": 0,
                        "channels": channels_seen,
                        "detail": channels_data.get("error", "Slack channel fetch failed"),
                    }
                channels.extend(channels_data.get("channels", []))
                cursor = (channels_data.get("response_metadata") or {}).get("next_cursor") or ""
                if not cursor:
                    break

            for channel in channels:
                channel_id = channel.get("id")
                if not channel_id:
                    continue
                channels_seen += 1
                channel_name = channel.get("name") or channel_id
                is_private = bool(channel.get("is_private"))
                _get_or_create_channel(
                    slack_id=channel_id,
                    name=channel_name,
                    team_id=team_id,
                    is_private=is_private,
                )
                channels_synced += 1

                if not is_private and not channel.get("is_member"):
                    join_resp = client.post(
                        "https://slack.com/api/conversations.join",
                        headers=headers,
                        json={"channel": channel_id},
                    )
                    join_data = join_resp.json()
                    if join_data.get("ok"):
                        channel["is_member"] = True
                    elif join_data.get("error") not in {"already_in_channel", "method_not_supported_for_channel_type"}:
                        log.info(
                            "Slack join skipped for channel %s: %s",
                            channel_id,
                            join_data.get("error"),
                        )

                history_resp = client.get(
                    "https://slack.com/api/conversations.history",
                    headers=headers,
                    params={
                        "channel": channel_id,
                        "oldest": oldest,
                        "limit": "100",
                    },
                )
                history_data = history_resp.json()
                if not history_data.get("ok"):
                    log.info(
                        "Slack history skipped for channel %s: %s",
                        channel_id,
                        history_data.get("error"),
                    )
                    continue

                for message in history_data.get("messages", []):
                    if message.get("subtype") in {"message_changed", "message_deleted"}:
                        continue
                    message["channel"] = channel_id
                    if _save_slack_message_for_user(
                        user_id=user_id,
                        event=message,
                        channel_name=channel_name,
                        team_id=team_id,
                    ):
                        fetched += 1
    except Exception as exc:
        log.warning("fetch_latest_slack_for_user failed: %s", exc)
        return {"ok": False, "fetched": fetched, "channels": channels_seen, "detail": str(exc)}

    return {"ok": True, "fetched": fetched, "channels": channels_synced, "detail": "Slack fetch complete"}


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
        log.warning("SLACK_SIGNING_SECRET not configured - skipping signature check!")
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

def _resolve_channel_name(channel_id: str, team_id: Optional[str] = None) -> Optional[str]:
    bot = _team_bot_token(team_id or "") or _bot_token()
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

# ── 1. Slack Events API (webhook - HMAC verified) ─────────────────────────────

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
        subtype = event.get("subtype")
        if subtype == "message_deleted":
            previous = event.get("previous_message") if isinstance(event.get("previous_message"), dict) else {}
            _delete_slack_message_by_ts(
                ts=event.get("deleted_ts") or previous.get("ts") or event.get("ts"),
                slack_user_id=previous.get("user") or event.get("user"),
            )
            return Response(status_code=200)

        if subtype == "message_changed":
            message = event.get("message") if isinstance(event.get("message"), dict) else {}
            channel_id = event.get("channel") or message.get("channel") or ""
            channel_name = _resolve_channel_name(channel_id, payload.get("team_id")) if channel_id else None
            _update_slack_message(event, channel_name)
            return Response(status_code=200)

        # Skip bot messages and unsupported message subtypes
        if event.get("bot_id") or subtype in ("bot_message",):
            return Response(status_code=200)

        # Propagate team_id from outer envelope if missing in event
        if not event.get("team"):
            event["team"] = payload.get("team_id", "")

        # Try to resolve channel name (best-effort)
        channel_id   = event.get("channel", "")
        channel_name = _resolve_channel_name(channel_id, payload.get("team_id")) if channel_id else None

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
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import PydanticOutputParser  # type: ignore
        from pydantic import BaseModel
        from ..llm_factory import get_llm

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
        llm = get_llm(provider="groq", model="llama-3.1-8b-instant", temperature=0)
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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token, bot_token FROM public.slack_auth WHERE user_id = %s LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")
    finally:
        conn.close()

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

    conn = _get_conn()
    try:
        global _last_channel_backfill
        cur = conn.cursor()
        import time as _time
        if _time.time() - _last_channel_backfill > 60:
            cur.execute(
                """
                UPDATE public.slack_messages sm
                SET channel_name = sc.name
                FROM public.slack_channels sc
                WHERE sm.channel_id = sc.id
                  AND sm.user_id = %s
                  AND sm.channel_name IS NULL
                  AND sc.name IS NOT NULL
                """,
                (user_id,),
            )
            conn.commit()
            _last_channel_backfill = _time.time()
        if channel:
            cur.execute(
                """
                SELECT *
                FROM (
                    SELECT id, user_id, slack_user_id, slack_team_id, slack_channel_id,
                           channel_name, text, ts, thread_ts, message_type, raw_payload,
                           created_at
                    FROM public.slack_messages
                    WHERE user_id = %s
                      AND created_at > NOW() - INTERVAL '7 days'
                      AND (
                          LOWER(channel_name) = LOWER(%s)
                          OR slack_channel_id = %s
                      )
                    ORDER BY created_at DESC
                    LIMIT %s
                ) recent
                ORDER BY created_at ASC
                """,
                (user_id, channel.lstrip("#"), channel, limit),
            )
        else:
            cur.execute(
                """
                SELECT *
                FROM (
                    SELECT id, user_id, slack_user_id, slack_team_id, slack_channel_id,
                           channel_name, text, ts, thread_ts, message_type, raw_payload,
                           created_at
                    FROM public.slack_messages
                    WHERE user_id = %s
                      AND created_at > NOW() - INTERVAL '7 days'
                    ORDER BY created_at DESC
                    LIMIT %s
                ) recent
                ORDER BY created_at ASC
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
    finally:
        conn.close()


# ── 4. Channels ───────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[SlackChannelOut], summary="List tracked Slack channels")
def get_slack_channels(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    team_id = None
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT slack_team_id
            FROM public.slack_auth
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        auth_row = cur.fetchone()
        if not auth_row:
            cur.close()
            return []
        team_id = auth_row[0]

        cur.execute(
            """
            SELECT sc.id, sc.slack_id, sc.name, sc.team_id, sc.is_private, sc.created_at
            FROM public.slack_channels sc
            WHERE sc.team_id = %s
            ORDER BY sc.name ASC
            """,
            (team_id,),
        )
        rows = cur.fetchall()
        chs  = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
    except Exception as exc:
        log.error("get_slack_channels failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch channels")
    finally:
        conn.close()

    if not chs and team_id:
        sync_result = fetch_latest_slack_for_user(user_id)
        if not sync_result.get("ok"):
            detail = sync_result.get("detail") or "Slack channel sync failed"
            raise HTTPException(status_code=502, detail=f"Slack sync failed: {detail}")

        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT sc.id, sc.slack_id, sc.name, sc.team_id, sc.is_private, sc.created_at
                FROM public.slack_channels sc
                WHERE sc.team_id = %s
                ORDER BY sc.name ASC
                """,
                (team_id,),
            )
            rows = cur.fetchall()
            chs = [_row_to_dict(r, cur.description) for r in rows]
            cur.close()
        except Exception as exc:
            log.error("get_slack_channels post-sync fetch failed: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to fetch synced channels")
        finally:
            conn.close()

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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT slack_user_id, slack_team_id, team_name, bot_token FROM public.slack_auth WHERE user_id = %s",
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
                bot_configured=bool(_bot_token() or row[3]),
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
