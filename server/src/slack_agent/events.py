"""Slack Events API handling, history sync and task extraction (NUMA-105 P3,
PLAN 16.2).

The /slack/events webhook body lives here as handle_slack_events(); router.py
keeps the thin route that delegates to it. Extracted verbatim from
slack_agent/router.py; router.py re-exports these names.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from ..core.timezones import user_today
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

# Delivered event ids, so a redelivery is acked without being worked again
# (NUMA-142 P6, PLAN 7). A fast ack makes retries unlikely but cannot prevent
# them: a dropped ack, a proxy 502 or a restart between the send and the
# background task all make Slack send the same event again, and the handler
# bills another model call per mentioned user and rewrites a task the user may
# have finished since. Bounded and expiring, because this outlives the request.
# It is per-process, which covers the common case (the retry lands on the worker
# that answered) and degrades to today's behaviour when it does not.
_EVENT_ID_TTL_SECONDS = 900
_EVENT_ID_MAX = 2048
_seen_event_ids: "OrderedDict[str, float]" = OrderedDict()
_seen_lock = threading.Lock()

# How many times the post-ack worker retries before the event is lost. The ack
# already went out, so Slack will not redeliver on a failure here and there is
# no queue to replay from; a bounded retry covers the brief Postgres or embedder
# outage this handler actually sees.
_PROCESS_ATTEMPTS = 3
_PROCESS_BACKOFF_SECONDS = 2.0


def _claim_event(event_id: str) -> bool:
    """True the first time an event id is seen, False for a redelivery."""
    if not event_id:
        return True

    now = time.time()
    with _seen_lock:
        while _seen_event_ids:
            oldest_id, seen_at = next(iter(_seen_event_ids.items()))
            if now - seen_at <= _EVENT_ID_TTL_SECONDS and len(_seen_event_ids) <= _EVENT_ID_MAX:
                break
            _seen_event_ids.pop(oldest_id, None)

        if event_id in _seen_event_ids:
            return False
        _seen_event_ids[event_id] = now
        return True


def _release_event(event_id: str) -> None:
    """Forget an event that never got processed, so a redelivery can retry it."""
    if not event_id:
        return
    with _seen_lock:
        _seen_event_ids.pop(event_id, None)


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

    This is the only route in the app without a JWT dependency, so the signature
    is the whole of its authentication: an unverifiable request is refused, never
    trusted (NUMA-129 P6, PLAN 8).

    Reading the body and checking the signature are the only parts that belong
    on the event loop. Everything after that is synchronous - the database, a
    blocking Slack SDK call, and an LLM round trip for @mentions - and it used to
    run inline in this `async def`, so one webhook blocked every other request in
    the process for as long as it took (NUMA-136 P6, PLAN 7).

    The ack now goes out before that work starts (NUMA-137 P6, PLAN 7). Slack
    gives a webhook 3 seconds and retries up to three times when it does not
    answer in time, and the @mention path runs a model, which does not fit in
    three seconds. Every retry re-ran the whole handler: three LLM calls billed
    for one message, and a task whose title was whatever the last answer said.
    The signature check still decides 403 and 503 before anything is accepted;
    what moves behind the ack is only what happens to an event already proven to
    be Slack's.
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

    # A retry means the previous delivery was not acked in time, which after this
    # change should not happen; say so once rather than leaving it invisible.
    retry_num = request.headers.get("X-Slack-Retry-Num")
    if retry_num:
        log.warning(
            "Slack redelivered an event (attempt %s, reason %s)",
            retry_num, request.headers.get("X-Slack-Retry-Reason", "unknown"),
        )

    # Detecting the retry header was never enough: the event was then processed
    # exactly as a first delivery. The id is what makes the second delivery a
    # no-op (NUMA-142 P6, PLAN 7).
    event_id = str(payload.get("event_id") or "")
    if not _claim_event(event_id):
        log.info("Slack event %s already handled; acking the redelivery", event_id)
        return Response(status_code=200)

    # ── Handle event callbacks ─────────────────────────────────────────────────
    # Answer first, work after. Starlette runs the background task once the
    # response is on the wire, and a sync task there goes to the same worker
    # threadpool NUMA-136 moved this into.
    return Response(
        status_code=200,
        background=BackgroundTask(_process_event, payload, event_id),
    )


def _event_identity(payload: dict, event_id: str) -> str:
    """Enough of an event to find it in Slack after a failure."""
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    return (
        f"event_id={event_id or 'unknown'} "
        f"team={payload.get('team_id') or 'unknown'} "
        f"channel={event.get('channel') or 'unknown'} "
        f"ts={event.get('ts') or 'unknown'}"
    )


def _process_event(payload: dict, event_id: str = "") -> None:
    """Run the handler after the ack, retrying a transient failure.

    Nothing is left to return a status to: the 200 has already gone out, so
    Slack will not redeliver and there is no queue to replay from. Answering
    first therefore removed the only retry path a brief Postgres or embedder
    outage had, and the message was lost with a log line that named nothing to
    recover it by. The bounded retry restores that, and the final log carries
    the event id, channel and ts (NUMA-142 P6, PLAN 7).

    The first attempt runs here, on the worker thread Starlette gave the
    background task. The retries do not: their backoff would hold one of the
    anyio threadpool's workers for seconds, and a Slack burst during a database
    outage would starve every other sync route in the process of threads
    (NUMA-142 P6 review). They go to a short-lived thread of their own instead.
    """
    try:
        _handle_event_payload(payload)
        return
    except Exception:
        log.warning(
            "Slack event processing failed (attempt 1/%d), retrying off the request pool: %s",
            _PROCESS_ATTEMPTS, _event_identity(payload, event_id),
            exc_info=True,
        )

    worker = threading.Thread(
        target=_retry_event,
        args=(payload, event_id),
        name="slack-event-retry",
        daemon=True,
    )
    worker.start()


def _retry_event(payload: dict, event_id: str) -> None:
    """The remaining attempts, on a thread that is nobody else's to wait for."""
    for attempt in range(2, _PROCESS_ATTEMPTS + 1):
        time.sleep(_PROCESS_BACKOFF_SECONDS * (attempt - 1))
        try:
            _handle_event_payload(payload)
            return
        except Exception:
            if attempt < _PROCESS_ATTEMPTS:
                log.warning(
                    "Slack event processing failed (attempt %d/%d), retrying: %s",
                    attempt, _PROCESS_ATTEMPTS, _event_identity(payload, event_id),
                    exc_info=True,
                )
                continue

    # Forget the id so a later redelivery, or a manual replay, is not swallowed
    # by the dedupe guard.
    _release_event(event_id)
    log.error(
        "Slack event dropped after %d attempts: %s",
        _PROCESS_ATTEMPTS, _event_identity(payload, event_id),
        exc_info=True,
    )


def _handle_event_payload(payload: dict) -> None:
    """The blocking half of the webhook: database, Slack SDK, task extraction.

    Runs in a worker thread. Every path returns None; the route answers 200
    regardless, as it did when this was inline.
    """
    event = payload.get("event", {})
    if event.get("type", "") != "message":
        return

    subtype = event.get("subtype")
    if subtype == "message_deleted":
        previous = event.get("previous_message") if isinstance(event.get("previous_message"), dict) else {}
        _delete_slack_message_by_ts(
            ts=event.get("deleted_ts") or previous.get("ts") or event.get("ts"),
            slack_user_id=previous.get("user") or event.get("user"),
        )
        return

    if subtype == "message_changed":
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        channel_id = event.get("channel") or message.get("channel") or ""
        channel_name = _resolve_channel_name(channel_id, payload.get("team_id")) if channel_id else None
        _update_slack_message(event, channel_name)
        return

    # Skip bot messages and unsupported message subtypes
    if event.get("bot_id") or subtype in ("bot_message",):
        return

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


def _run_agent_task_extraction(text: str, ts: Optional[str], team_id: Optional[str]):
    """Background call: extract action items from @mentioned messages.

    The extraction is a deterministic question about one message, so it runs
    once and the answer is written for every mentioned NUMA user. It used to run
    per user: three mentions billed three identical model calls (NUMA-142 P6,
    PLAN 9).
    """
    try:
        import re
        mentioned_slack_ids = re.findall(r"<@([A-Z0-9]+)>", text)
        if not mentioned_slack_ids:
            return
        rows = slack_repository.user_ids_by_slack_ids(mentioned_slack_ids)
        user_ids = [str(user_id_row) for user_id_row, _slack_id in rows]
        if not user_ids:
            return

        # One extraction serves everyone, but which user's provider runs it
        # matters: if the first mentioned user has no working provider the
        # answer must not be "no task for anyone", so the next one is tried
        # (NUMA-142 P6 review). A success stops the loop, so the common case is
        # still exactly one model call.
        extraction = None
        for owner_id in user_ids:
            extraction = _extract_task_from_text(text, owner_id)
            if extraction is not None:
                break
        if not extraction:
            return

        for user_id in user_ids:
            _create_task_from_extraction(extraction, ts, user_id)
    except Exception as exc:
        log.warning("_run_agent_task_extraction error: %s", exc)


def _extract_task_from_text(text: str, user_id: str) -> Optional[dict]:
    """Ask the LLM whether a Slack message is actionable. One call per message.

    The provider is the mentioned user's own, not a hardcoded Groq: a user
    configured for OpenAI got a silent no-op here because GROQ_API_KEY was never
    set on the box (NUMA-142 P6, PLAN 9).
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import PydanticOutputParser  # type: ignore
        from pydantic import BaseModel
        from ..core.llm_factory import get_llm

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
        llm = get_llm(user_id=user_id, temperature=0)
        chain = prompt | llm | parser
        result: TaskExtraction = chain.invoke({
            "text": text,
            # The mentioned user's day, not the host's, like every other
            # "today" in this sweep. One extraction serves every mentioned user,
            # so a workspace spanning zones still resolves "tomorrow" against
            # this one user's date; that is the cost of not billing a model call
            # per mention (NUMA-142 P6 review).
            "today": user_today(user_id).isoformat(),
            "format_instructions": parser.get_format_instructions(),
        })
        if not result.is_actionable or not result.task_title:
            return None
        return {
            "title": result.task_title,
            "priority": result.task_priority,
            "due": result.task_due,
        }
    except Exception as exc:
        log.warning("_extract_task_from_text failed: %s", exc)
        return None


def _create_task_from_extraction(extraction: dict, ts: Optional[str], user_id: str) -> None:
    """Write one already-extracted action item as a task for one user."""
    try:
        from .agent import _insert_task_from_slack

        priority = extraction.get("priority")
        _insert_task_from_slack(
            user_id=user_id,
            title=extraction["title"],
            priority=priority if priority in {"low", "medium", "high", "urgent"} else "medium",
            due_date=extraction.get("due"),
            slack_ts=ts,
        )
    except Exception as exc:
        log.warning("_create_task_from_extraction failed: %s", exc)
