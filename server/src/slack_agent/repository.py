"""Slack data-access layer (NUMA-115, PLAN 6/18/21). SQL only.

Extracted verbatim from slack_agent/router.py and slack_agent/service.py. The
router/service wrappers keep their swallow/log/return semantics; these methods
run the raw SQL and (for writes) rollback+raise on error.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict

# Column projections (constant, never interpolated with caller input).
_MSG_COLS_ROUTER = (
    "id, user_id, slack_user_id, slack_team_id, slack_channel_id, "
    "channel_name, text, ts, thread_ts, message_type, raw_payload, created_at"
)
_MSG_COLS_SERVICE = (
    "id, user_id, slack_user_id, slack_channel_id, channel_name, text, ts, "
    "thread_ts, message_type, created_at"
)
_CHANNEL_COLS = "sc.id, sc.slack_id, sc.name, sc.team_id, sc.is_private, sc.created_at"
_TASK_RETURNING = (
    "id, user_id, title, description, status, priority, "
    "due_date, reminder_at, source_name, source_logo, "
    "external_ref, position, completed_at, created_at, updated_at"
)


class SlackRepository(BaseRepository):
    # ── Channels ──────────────────────────────────────────────────────────────
    def get_or_create_channel(
        self, slack_id: str, name: Optional[str], team_id: str, is_private: bool,
    ) -> str:
        with get_db() as conn:
            cur = conn.cursor()
            try:
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
                    return str(channel_id)
                cur.execute(
                    "INSERT INTO public.slack_channels (slack_id, name, team_id, is_private) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (slack_id, name, team_id, is_private),
                )
                new_id = str(cur.fetchone()[0])
                conn.commit()
                return new_id
            except Exception:
                conn.rollback()
                raise

    def channel_name(self, slack_id: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM public.slack_channels WHERE slack_id = %s LIMIT 1",
                (slack_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def channels_for_team(self, team_id: str) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _CHANNEL_COLS + " FROM public.slack_channels sc "
                "WHERE sc.team_id = %s ORDER BY sc.name ASC",
                (team_id,),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    # ── slack_auth ────────────────────────────────────────────────────────────
    def user_id_by_slack(self, slack_user_id: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM public.slack_auth WHERE slack_user_id = %s LIMIT 1",
                (slack_user_id,),
            )
            row = cur.fetchone()
            return str(row[0]) if row else None

    def user_ids_for_team(self, team_id: str) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM public.slack_auth WHERE slack_team_id = %s",
                (team_id,),
            )
            return cur.fetchall() or []

    def team_bot_token(self, team_id: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT bot_token, access_token FROM public.slack_auth "
                "WHERE slack_team_id = %s ORDER BY updated_at DESC LIMIT 1",
                (team_id,),
            )
            return cur.fetchone()

    def all_user_ids(self) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM public.slack_auth")
            return cur.fetchall() or []

    def auth_tokens_for_user(self, user_id: str):
        """(access_token, bot_token, slack_team_id) or None."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT access_token, bot_token, slack_team_id "
                "FROM public.slack_auth WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            return cur.fetchone()

    def send_tokens_for_user(self, user_id: str):
        """(access_token, bot_token) or None."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT access_token, bot_token FROM public.slack_auth "
                "WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            return cur.fetchone()

    def status_for_user(self, user_id: str):
        """(slack_user_id, slack_team_id, team_name, bot_token) or None."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT slack_user_id, slack_team_id, team_name, bot_token "
                "FROM public.slack_auth WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()

    def team_id_for_user(self, user_id: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT slack_team_id FROM public.slack_auth WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            return cur.fetchone()

    def slack_tokens_for_user(self, user_id: str):
        """(bot_token, access_token) or None (service token lookup)."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT bot_token, access_token FROM public.slack_auth "
                "WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            return cur.fetchone()

    def user_ids_by_slack_ids(self, slack_ids: list) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, slack_user_id FROM public.slack_auth "
                "WHERE slack_user_id = ANY(%s)",
                (slack_ids,),
            )
            return cur.fetchall()

    def upsert_auth(
        self, user_id: str, slack_user_id: str, slack_team_id: str,
        access_token: str, bot_token: Optional[str], team_name: Optional[str],
        authed_user_json: Optional[str],
    ) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.slack_auth "
                    "(user_id, slack_user_id, slack_team_id, access_token, bot_token, team_name, authed_user_obj) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (user_id) DO UPDATE SET "
                    "    slack_user_id = EXCLUDED.slack_user_id, "
                    "    slack_team_id = EXCLUDED.slack_team_id, "
                    "    access_token = EXCLUDED.access_token, "
                    "    bot_token = EXCLUDED.bot_token, "
                    "    team_name = EXCLUDED.team_name, "
                    "    authed_user_obj = EXCLUDED.authed_user_obj, "
                    "    updated_at = NOW()",
                    (user_id, slack_user_id, slack_team_id, access_token, bot_token,
                     team_name, authed_user_json),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ── slack_messages ────────────────────────────────────────────────────────
    def save_message(
        self, user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
        channel_name, text, ts, thread_ts, message_type, raw_json,
    ) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.slack_messages "
                    "(user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id, "
                    " channel_name, text, ts, thread_ts, message_type, raw_payload) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (ts) DO UPDATE SET "
                    "    user_id = COALESCE(public.slack_messages.user_id, EXCLUDED.user_id), "
                    "    slack_team_id = EXCLUDED.slack_team_id, "
                    "    channel_id = COALESCE(public.slack_messages.channel_id, EXCLUDED.channel_id), "
                    "    slack_channel_id = EXCLUDED.slack_channel_id, "
                    "    channel_name = COALESCE(EXCLUDED.channel_name, public.slack_messages.channel_name), "
                    "    text = EXCLUDED.text, "
                    "    thread_ts = EXCLUDED.thread_ts, "
                    "    message_type = EXCLUDED.message_type, "
                    "    raw_payload = EXCLUDED.raw_payload",
                    (user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
                     channel_name, text, ts, thread_ts, message_type, raw_json),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def save_message_for_user(
        self, user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
        channel_name, text, ts, thread_ts, message_type, raw_json, created_at,
    ) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.slack_messages "
                    "(user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id, "
                    " channel_name, text, ts, thread_ts, message_type, raw_payload, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (ts) DO UPDATE SET "
                    "    user_id = EXCLUDED.user_id, "
                    "    slack_user_id = EXCLUDED.slack_user_id, "
                    "    slack_team_id = EXCLUDED.slack_team_id, "
                    "    channel_id = COALESCE(EXCLUDED.channel_id, public.slack_messages.channel_id), "
                    "    slack_channel_id = EXCLUDED.slack_channel_id, "
                    "    channel_name = COALESCE(EXCLUDED.channel_name, public.slack_messages.channel_name), "
                    "    text = EXCLUDED.text, "
                    "    thread_ts = EXCLUDED.thread_ts, "
                    "    message_type = EXCLUDED.message_type, "
                    "    raw_payload = EXCLUDED.raw_payload, "
                    "    created_at = EXCLUDED.created_at",
                    (user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
                     channel_name, text, ts, thread_ts, message_type, raw_json, created_at),
                )
                inserted = cur.rowcount
                conn.commit()
                return inserted
            except Exception:
                conn.rollback()
                raise

    def update_message(self, text, channel_name, raw_json, ts) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE public.slack_messages "
                    "SET text = %s, channel_name = COALESCE(%s, channel_name), raw_payload = %s "
                    "WHERE ts = %s",
                    (text, channel_name, raw_json, ts),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def user_id_by_message_ts(self, ts: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM public.slack_messages WHERE ts = %s LIMIT 1",
                (ts,),
            )
            row = cur.fetchone()
            return str(row[0]) if row and row[0] else None

    def delete_message_and_tasks(self, ts: str) -> list:
        """Delete the message + any linked slack tasks; return affected task ids."""
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT id, user_id FROM public.tasks WHERE external_ref = %s",
                    (f"slack:{ts}",),
                )
                task_ids = [str(r[0]) for r in (cur.fetchall() or []) if r and r[0]]
                cur.execute("DELETE FROM public.slack_messages WHERE ts = %s", (ts,))
                cur.execute(
                    "DELETE FROM public.tasks WHERE external_ref = %s",
                    (f"slack:{ts}",),
                )
                conn.commit()
                return task_ids
            except Exception:
                conn.rollback()
                raise

    def backfill_channel_names(self, user_id: str) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE public.slack_messages sm SET channel_name = sc.name "
                "FROM public.slack_channels sc "
                "WHERE sm.channel_id = sc.id AND sm.user_id = %s "
                "  AND sm.channel_name IS NULL AND sc.name IS NOT NULL",
                (user_id,),
            )
            conn.commit()

    def list_messages(self, user_id: str, channel: Optional[str], limit: int) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            if channel:
                cur.execute(
                    "SELECT * FROM ("
                    "    SELECT " + _MSG_COLS_ROUTER + " "
                    "    FROM public.slack_messages "
                    "    WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days' "
                    "      AND (LOWER(channel_name) = LOWER(%s) OR slack_channel_id = %s) "
                    "    ORDER BY created_at DESC LIMIT %s"
                    ") recent ORDER BY created_at ASC",
                    (user_id, channel.lstrip("#"), channel, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM ("
                    "    SELECT " + _MSG_COLS_ROUTER + " "
                    "    FROM public.slack_messages "
                    "    WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days' "
                    "    ORDER BY created_at DESC LIMIT %s"
                    ") recent ORDER BY created_at ASC",
                    (user_id, limit),
                )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def recent_messages(self, user_id: str, limit: int, channel_name: Optional[str]) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            if channel_name:
                cur.execute(
                    "SELECT " + _MSG_COLS_SERVICE + " FROM public.slack_messages "
                    "WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days' "
                    "  AND (LOWER(channel_name) = LOWER(%s) OR slack_channel_id = %s) "
                    "ORDER BY created_at DESC LIMIT %s",
                    (user_id, channel_name, channel_name, limit),
                )
            else:
                cur.execute(
                    "SELECT " + _MSG_COLS_SERVICE + " FROM public.slack_messages "
                    "WHERE user_id = %s AND created_at > NOW() - INTERVAL '7 days' "
                    "ORDER BY created_at DESC LIMIT %s",
                    (user_id, limit),
                )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def purge_old_messages(self) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "DELETE FROM public.slack_messages "
                    "WHERE created_at < NOW() - INTERVAL '7 days'"
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted
            except Exception:
                conn.rollback()
                raise

    # ── tasks (Slack-sourced) ─────────────────────────────────────────────────
    def insert_task_from_slack(
        self, user_id: str, title: str, description: Optional[str], status: str,
        priority: str, due: Optional[datetime], external_ref: str,
        completed_at: Optional[datetime],
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.tasks "
                    "(user_id, title, description, status, priority, due_date, "
                    " source_name, source_logo, external_ref, position, completed_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'Slack', 'slack', %s, 0, %s) "
                    "ON CONFLICT (user_id, external_ref) DO UPDATE SET "
                    "    title = EXCLUDED.title, "
                    "    description = EXCLUDED.description, "
                    "    status = EXCLUDED.status, "
                    "    priority = EXCLUDED.priority, "
                    "    due_date = EXCLUDED.due_date, "
                    "    completed_at = EXCLUDED.completed_at, "
                    "    updated_at = NOW() "
                    "RETURNING " + _TASK_RETURNING,
                    (user_id, title, description, status, priority, due, external_ref, completed_at),
                )
                row = cur.fetchone()
                task = row_to_dict(cur, row) if row else {}
                if task and task.get("id"):
                    cur.execute(
                        "DELETE FROM public.tasks "
                        "WHERE user_id = %s AND source_name = 'Slack' "
                        "  AND LOWER(title) = LOWER(%s) AND id <> %s "
                        "  AND (external_ref IS NULL OR external_ref = %s)",
                        (user_id, title, task["id"], external_ref),
                    )
                conn.commit()
                return task
            except Exception:
                conn.rollback()
                raise

    def list_slack_tasks(self, user_id: str, limit: int) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, status, priority, due_date, source_name, external_ref, created_at "
                "FROM public.tasks WHERE user_id = %s AND source_name = 'Slack' "
                "ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]


slack_repository = SlackRepository()
