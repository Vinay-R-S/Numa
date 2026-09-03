"""Slack Events API handling, history sync and task extraction (NUMA-105 P3,
PLAN 16.2).

The /slack/events webhook body lives here as handle_slack_events(); router.py
keeps the thin route that delegates to it. Extracted verbatim from
slack_agent/router.py; router.py re-exports these names.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .config import _bot_token
from .errors import (
    _is_transient_dependency_error,
    _temporary_unavailable_detail,
    _log_dependency_exception,
)
from .security import MISSING_SECRET_MESSAGE, signing_secret_configured, verify_slack_signature
from .client import _cache_workspace_user_names, _resolve_channel_name
from .persistence import (
    _get_or_create_channel,
    _save_slack_message,
    _save_slack_message_for_user,
    _update_slack_message,
    _delete_slack_message_by_ts,
)
from .repository import slack_repository

log = logging.getLogger(__name__)


def fetch_latest_slack_for_user(user_id: str) -> dict:
    """Fetch the last 7 days of Slack channel messages for one connected user."""
    if not user_id:
        return {"ok": False, "fetched": 0, "channels": 0, "detail": "Missing user id"}

    try:
        row = slack_repository.auth_tokens_for_user(user_id)
    except Exception as exc:
        _log_dependency_exception("fetch_latest_slack_for_user auth lookup failed: %s", exc)
        detail = _temporary_unavailable_detail("Slack database") if _is_transient_dependency_error(exc) else str(exc)
        return {"ok": False, "fetched": 0, "channels": 0, "detail": detail}

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
        _log_dependency_exception("fetch_latest_slack_for_user failed: %s", exc)
        detail = _temporary_unavailable_detail("Slack") if _is_transient_dependency_error(exc) else str(exc)
        return {"ok": False, "fetched": fetched, "channels": channels_seen, "detail": detail}

    return {"ok": True, "fetched": fetched, "channels": channels_synced, "detail": "Slack fetch complete"}


async def handle_slack_events(request: Request):
    """
    Receives Slack events via the Events API.
    Uses HMAC-SHA256 signature verification to confirm authenticity.
    Responds within 3 seconds as required by Slack's API contract.

    This is the only route in the app without a JWT dependency, so the signature
    is the whole of its authentication: an unverifiable request is refused, never
    trusted (NUMA-129 P6, PLAN 8).
    """
    body_bytes = await request.body()

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # 503, not 403, when the secret is unset: the request may be perfectly valid
    # and the server is the one that cannot check it. The log names the variable
    # and how to fix it; the response does not, since this caller is
    # unauthenticated.
    if not signing_secret_configured():
        log.error("Slack event refused: %s", MISSING_SECRET_MESSAGE)
        raise HTTPException(
            status_code=503,
            detail="Slack signature verification is not configured",
        )

    if not verify_slack_signature(body_bytes, timestamp, signature):
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
        rows = slack_repository.user_ids_by_slack_ids(mentioned_slack_ids)

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
            from .agent import _insert_task_from_slack
            _insert_task_from_slack(
                user_id=user_id,
                title=result.task_title,
                priority=result.task_priority if result.task_priority in {"low","medium","high","urgent"} else "medium",
                due_date=result.task_due,
                slack_ts=ts,
            )
    except Exception as exc:
        log.warning("_extract_and_create_task failed: %s", exc)
