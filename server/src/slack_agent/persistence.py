"""Slack message/auth persistence and lookup wrappers (NUMA-105 P3, PLAN 16.2).

Orchestration over the pure-SQL SlackRepository (Phase 2) plus best-effort Qdrant
ingest. PLAN 16.2 sketched these into repository.py, but that file became a
pure-SQL class in Phase 2, so the orchestration wrappers live here to keep the
repository free of business rules (PLAN 2.1). Extracted verbatim from
slack_agent/router.py; router.py re-exports these names.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from .repository import slack_repository
from .errors import _log_dependency_exception
from .qdrant_store import delete_message, ingest_message

log = logging.getLogger(__name__)


def _get_or_create_channel(
    slack_id: str,
    name: Optional[str],
    team_id: str,
    is_private: bool = False,
) -> Optional[str]:
    """Return the UUID of a slack_channels row, creating it if necessary."""
    try:
        return slack_repository.get_or_create_channel(slack_id, name, team_id, is_private)
    except Exception as exc:
        log.warning("_get_or_create_channel failed: %s", exc)
        return None


def _get_channel_name_from_db(slack_id: str) -> Optional[str]:
    try:
        return slack_repository.channel_name(slack_id)
    except Exception:
        return None


def _resolve_user_id_by_slack(slack_user_id: str) -> Optional[str]:
    """Return NUMA user_id for a given Slack user id (from slack_auth table)."""
    try:
        return slack_repository.user_id_by_slack(slack_user_id)
    except Exception as exc:
        log.warning("_resolve_user_id_by_slack failed: %s", exc)
        return None


def _user_ids_for_slack_team(team_id: str) -> list[str]:
    if not team_id:
        return []

    try:
        rows = slack_repository.user_ids_for_team(team_id)
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as exc:
        _log_dependency_exception("_user_ids_for_slack_team failed: %s", exc)
        return []


def _team_bot_token(team_id: str) -> Optional[str]:
    if not team_id:
        return None

    try:
        row = slack_repository.team_bot_token(team_id)
        if not row:
            return None
        return (row[0] or row[1] or "").strip() or None
    except Exception as exc:
        log.warning("_team_bot_token failed: %s", exc)
        return None


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

    try:
        slack_repository.save_message(
            user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
            resolved_channel_name, text, ts, event.get("thread_ts"), "message",
            json.dumps(event),
        )
    except Exception as exc:
        log.warning("_save_slack_message DB insert failed: %s", exc)
        return

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
        try:
            user_id = slack_repository.user_id_by_message_ts(ts)
        except Exception as exc:
            log.warning("_delete_slack_message_by_ts lookup failed: %s", exc)

    task_ids: list[str] = []
    try:
        task_ids = slack_repository.delete_message_and_tasks(ts)
    except Exception as exc:
        log.warning("_delete_slack_message_by_ts DB delete failed: %s", exc)

    if user_id:
        delete_message(user_id=user_id, ts=ts)
        try:
            from ..tasks import service as task_service
            for task_id in task_ids:
                task_service.delete_task_snapshot(user_id, task_id)
        except Exception:
            log.debug("Task snapshot cleanup failed for ts %s", ts, exc_info=True)


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
    try:
        slack_repository.update_message(text, resolved_channel_name, json.dumps(event), ts)
    except Exception as exc:
        log.warning("_update_slack_message DB update failed: %s", exc)
        return

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

    inserted = False
    try:
        rowcount = slack_repository.save_message_for_user(
            user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
            resolved_channel_name, text, ts, event.get("thread_ts"),
            event.get("subtype") or "message", json.dumps(event), created_at,
        )
        inserted = rowcount > 0
    except Exception as exc:
        log.warning("_save_slack_message_for_user DB insert failed: %s", exc)
        return False

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


def _upsert_slack_auth(
    user_id: str,
    slack_user_id: str,
    slack_team_id: str,
    access_token: str,
    bot_token: Optional[str],
    team_name: Optional[str],
    authed_user_obj: Optional[dict],
):
    try:
        slack_repository.upsert_auth(
            user_id, slack_user_id, slack_team_id, access_token, bot_token, team_name,
            json.dumps(authed_user_obj) if authed_user_obj else None,
        )
    except Exception as exc:
        log.warning("_upsert_slack_auth failed: %s", exc)


def get_all_connected_slack_user_ids() -> list[str]:
    try:
        rows = slack_repository.all_user_ids()
        return [str(row[0]) for row in rows]
    except Exception as exc:
        _log_dependency_exception("get_all_connected_slack_user_ids failed: %s", exc)
        return []
