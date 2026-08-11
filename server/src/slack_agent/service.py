"""Slack feature service (NUMA-115 P4, PLAN 2.1 / 5.2 / 21.1).

`SlackService` owns the orchestration that used to sit inside the HTTP routes:
status lookup, channel listing with its sync fallback, message listing with the
throttled channel-name backfill, outbound messages, history sync and the purge
job. Dependencies (repository, Slack Web API callables, sync entrypoint) are
injected through the constructor.

The LangGraph sub-agent moved to `agent.py`; its public entrypoints are
re-exported here so `master_agent.orchestrator` and the event handlers keep
their existing import paths.

Errors: methods raise `core.errors.AppError` with the status code the route used
to raise directly; `router._http_error` maps them back to HTTP.
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from ..core.base import BaseService
from ..core.errors import AppError, UpstreamError
from .agent import (  # noqa: F401  re-exported for existing import paths
    SLACK_AGENT_SYSTEM_PROMPT,
    SlackAgentState,
    _create_tasks_from_recent_slack,
    _fetch_recent_db_messages,
    _insert_task_from_slack,
    _list_slack_tasks,
    run_slack_agent_chat,
)
from .client import _resolve_slack_user_name, post_chat_message
from .config import _bot_token
from .errors import (
    _is_transient_dependency_error,
    _log_dependency_exception,
    _temporary_unavailable_detail,
)
from .events import fetch_latest_slack_for_user
from .qdrant_store import purge_old_messages as purge_old_qdrant_messages
from .repository import SlackRepository, slack_repository

CHANNEL_BACKFILL_INTERVAL_SECONDS = 60
BACKFILL_STAMP_LIMIT = 512


class SlackService(BaseService):
    """Slack workspace orchestration behind the /slack routes."""

    def __init__(
        self,
        repository: Optional[SlackRepository] = None,
        sync_history: Optional[Callable[[str], dict]] = None,
        resolve_user_name: Optional[Callable[..., Optional[str]]] = None,
        send_message_api: Optional[Callable[..., dict]] = None,
        purge_vectors: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.repository = repository or slack_repository
        self.sync_history = sync_history or fetch_latest_slack_for_user
        self.resolve_user_name = resolve_user_name or _resolve_slack_user_name
        self.send_message_api = send_message_api or post_chat_message
        self.purge_vectors = purge_vectors or purge_old_qdrant_messages
        # Per user: this is a process-wide singleton, so one shared timestamp
        # would let the first caller suppress every other user's backfill.
        self._last_channel_backfill: dict[str, float] = {}

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat(
        self,
        query: str,
        history: List[dict],
        user_id: Optional[str],
        model: Optional[str] = None,
    ) -> Dict:
        return run_slack_agent_chat(query=query, history=history, user_id=user_id, model=model)

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self, user_id: str) -> Dict:
        """Connection status. A DB failure reads as disconnected, as before."""
        try:
            row = self.repository.status_for_user(user_id)
        except Exception as exc:
            self.log.error("get_slack_status failed: %s", exc)
            return {"connected": False}

        if not row:
            return {"connected": False, "bot_configured": bool(_bot_token())}

        return {
            "connected": True,
            "slack_user_id": row[0],
            "slack_team_id": row[1],
            "team_name": row[2],
            "bot_configured": bool(_bot_token() or row[3]),
        }

    # ── Channels ─────────────────────────────────────────────────────────────

    def list_channels(self, user_id: str) -> List[Dict]:
        """Tracked channels for the user's workspace, syncing once if empty."""
        try:
            auth_row = self.repository.team_id_for_user(user_id)
            if not auth_row:
                return []
            team_id = auth_row[0]
            channels = self.repository.channels_for_team(team_id)
        except Exception as exc:
            self.log.error("get_slack_channels failed: %s", exc)
            raise AppError("Failed to fetch channels") from exc

        if channels or not team_id:
            return [self._channel_dto(c) for c in channels]

        sync_result = self.sync_history(user_id)
        if not sync_result.get("ok"):
            detail = sync_result.get("detail") or "Slack channel sync failed"
            raise UpstreamError(f"Slack sync failed: {detail}")

        try:
            channels = self.repository.channels_for_team(team_id)
        except Exception as exc:
            self.log.error("get_slack_channels post-sync fetch failed: %s", exc)
            raise AppError("Failed to fetch synced channels") from exc

        return [self._channel_dto(c) for c in channels]

    @staticmethod
    def _channel_dto(row: Dict) -> Dict:
        return {
            "id": str(row["id"]),
            "slack_id": row["slack_id"],
            "name": row.get("name"),
            "team_id": row["team_id"],
            "is_private": row.get("is_private", False),
            "created_at": row.get("created_at"),
        }

    # ── Messages ─────────────────────────────────────────────────────────────

    def list_messages(self, user_id: str, channel: Optional[str], limit: int) -> List[Dict]:
        try:
            self._backfill_channel_names(user_id)
            rows = self.repository.list_messages(user_id, channel, limit)
            return [self._message_dto(row) for row in rows]
        except Exception as exc:
            self.log.error("get_slack_messages failed: %s", exc)
            raise AppError("Failed to fetch messages") from exc

    def _backfill_channel_names(self, user_id: str) -> None:
        """Fill in missing channel names at most once a minute per user."""
        now = time.time()
        if now - self._last_channel_backfill.get(user_id, 0.0) <= CHANNEL_BACKFILL_INTERVAL_SECONDS:
            return

        self.repository.backfill_channel_names(user_id)
        self._last_channel_backfill[user_id] = now
        self._prune_backfill_stamps(now)

    def _prune_backfill_stamps(self, now: float) -> None:
        """Drop expired stamps so the map cannot grow without bound."""
        if len(self._last_channel_backfill) <= BACKFILL_STAMP_LIMIT:
            return

        self._last_channel_backfill = {
            key: stamp
            for key, stamp in self._last_channel_backfill.items()
            if now - stamp <= CHANNEL_BACKFILL_INTERVAL_SECONDS
        }

    def _message_dto(self, row: Dict) -> Dict:
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "slack_user_id": row["slack_user_id"],
            "sender_name": self.resolve_user_name(
                str(row.get("slack_team_id") or ""),
                str(row.get("slack_user_id") or ""),
                row.get("raw_payload"),
            ),
            "slack_channel_id": row["slack_channel_id"],
            "channel_name": row.get("channel_name"),
            "text": row.get("text"),
            "ts": row["ts"],
            "thread_ts": row.get("thread_ts"),
            "message_type": row.get("message_type", "message"),
            "created_at": row.get("created_at"),
        }

    # ── Outbound message ─────────────────────────────────────────────────────

    def send_message(
        self,
        user_id: str,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> Dict:
        """Post to a channel with the user's token. Slack errors return ok=False."""
        try:
            row = self.repository.send_tokens_for_user(user_id)
        except Exception as exc:
            raise AppError(f"DB error: {exc}") from exc

        if not row:
            raise AppError("Slack not connected", status_code=400)

        access_token, bot_token = row
        token = (bot_token or access_token or _bot_token() or "").strip()
        if not token:
            raise AppError("No Slack token available", status_code=400)

        try:
            data = self.send_message_api(token, channel_id, text, thread_ts)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        if not data.get("ok"):
            return {"ok": False, "error": data.get("error", "Unknown error")}
        return {"ok": True, "ts": data.get("ts")}

    # ── Sync ─────────────────────────────────────────────────────────────────

    def sync_user(self, user_id: str) -> Dict:
        return self.sync_history(user_id)

    # ── Purge (scheduler) ────────────────────────────────────────────────────

    def purge_old_messages(self) -> Dict:
        """Drop Slack vectors and rows outside the 7-day window."""
        self.purge_vectors()

        try:
            deleted = self.repository.purge_old_messages()
        except Exception as exc:
            _log_dependency_exception("DB purge failed: %s", exc)
            message = (
                _temporary_unavailable_detail("Slack database")
                if _is_transient_dependency_error(exc)
                else str(exc)
            )
            return {"ok": False, "message": message}

        self.log.info("Purged %d slack_messages rows older than 7 days", deleted)
        return {"ok": True, "message": "Old Slack data purged (7-day window)"}


slack_service = SlackService()
