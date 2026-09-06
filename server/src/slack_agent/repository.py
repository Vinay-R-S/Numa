"""Slack data-access layer (NUMA-115, PLAN 6/18/21). SQL only.

Extracted verbatim from slack_agent/router.py and slack_agent/service.py. The
router/service wrappers keep their swallow/log/return semantics; these methods
run the raw SQL and (for writes) rollback+raise on error.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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
                # DO NOTHING, not a bare INSERT: `slack_id` is UNIQUE, and two
                # callers can now reach this at once, since NUMA-136 moved the
                # webhook off the event loop that used to serialise it. The
                # loser of that race used to raise a UniqueViolation, which the
                # caller turned into None and stored a message with no channel;
                # it re-reads the winner's row instead. No update semantics
                # change: those all live in the SELECT branch above.
                cur.execute(
                    "INSERT INTO public.slack_channels (slack_id, name, team_id, is_private) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (slack_id) DO NOTHING RETURNING id",
                    (slack_id, name, team_id, is_private),
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    return str(row[0])

                cur.execute(
                    "SELECT id FROM public.slack_channels WHERE slack_id = %s LIMIT 1",
                    (slack_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(
                        f"slack_channels row for {slack_id} disappeared after a conflict"
                    )
                return str(row[0])
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
        """Store a message, ordinarily the copy no NUMA user owns.

        Uniqueness moved from `ts` to `(user_id, ts)` (migration 0006), and
        Postgres counts NULLs as distinct, so an unowned row has to arbitrate on
        the partial index instead or every redelivery would insert a new row.
        The owned branch is here for completeness: the only caller passes None,
        but a future one passing a real id must not silently duplicate.
        """
        conflict_target = (
            "ON CONFLICT (user_id, ts)" if user_id else "ON CONFLICT (ts) WHERE user_id IS NULL"
        )
        with get_db() as conn:
            cur = conn.cursor()
            try:
                if not user_id:
                    # The partial index the unowned branch arbitrates on cannot
                    # see an owned row, so a redelivery that transiently found
                    # no NUMA owner would insert a second, unowned copy beside
                    # them. Reads all filter on user_id, so it was inert but
                    # accumulating (NUMA-142 P6).
                    cur.execute(
                        "SELECT 1 FROM public.slack_messages "
                        "WHERE ts = %s AND user_id IS NOT NULL LIMIT 1",
                        (ts,),
                    )
                    if cur.fetchone():
                        conn.commit()
                        return
                cur.execute(
                    "INSERT INTO public.slack_messages "
                    "(user_id, slack_user_id, slack_team_id, channel_id, slack_channel_id, "
                    " channel_name, text, ts, thread_ts, message_type, raw_payload) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    + conflict_target + " DO UPDATE SET "
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
                    # (user_id, ts), not ts: one row per user per message.
                    # Arbitrating on ts alone made the second NUMA user in a
                    # workspace steal the first user's row (NUMA-142 P6).
                    "ON CONFLICT (user_id, ts) DO UPDATE SET "
                    "    slack_user_id = EXCLUDED.slack_user_id, "
                    "    slack_team_id = EXCLUDED.slack_team_id, "
                    "    channel_id = COALESCE(EXCLUDED.channel_id, public.slack_messages.channel_id), "
                    "    slack_channel_id = EXCLUDED.slack_channel_id, "
                    "    channel_name = COALESCE(EXCLUDED.channel_name, public.slack_messages.channel_name), "
                    "    text = EXCLUDED.text, "
                    "    thread_ts = EXCLUDED.thread_ts, "
                    "    message_type = EXCLUDED.message_type, "
                    "    raw_payload = EXCLUDED.raw_payload, "
                    "    created_at = EXCLUDED.created_at "
                    # rowcount is 1 for an update too, so every re-sync reported
                    # each message as newly fetched. xmax is 0 only on a genuine
                    # insert (NUMA-142 P6).
                    "RETURNING (xmax = 0) AS inserted",
                    (user_id, slack_user_id, slack_team_id, channel_uuid, slack_chan_id,
                     channel_name, text, ts, thread_ts, message_type, raw_json, created_at),
                )
                row = cur.fetchone()

                # Migration 0006 moved ownership to (user_id, ts), and the
                # `ON CONFLICT (user_id, ts)` arbiter cannot see the old
                # `user_id IS NULL` rows the pre-0006 writer left behind. They
                # were adopted by the previous upsert and are now orphaned
                # forever, so an owned write clears the unowned copy of the same
                # message (NUMA-142 P6 review).
                cur.execute(
                    "DELETE FROM public.slack_messages WHERE ts = %s AND user_id IS NULL",
                    (ts,),
                )
                conn.commit()
                return 1 if row and row[0] else 0
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

    def user_ids_by_message_ts(self, ts: str) -> List[str]:
        """Every NUMA user holding a copy of this message.

        Was `user_id_by_message_ts`, a `LIMIT 1` that made sense while `ts` was
        globally unique. Since migration 0006 a message has one row per user, so
        picking one of them at random left the others' vectors behind.
        """
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT DISTINCT user_id FROM public.slack_messages "
                "WHERE ts = %s AND user_id IS NOT NULL",
                (ts,),
            )
            return [str(r[0]) for r in (cur.fetchall() or []) if r and r[0]]

    def delete_message_and_tasks(self, ts: str) -> List[Tuple[str, str]]:
        """Delete the message rows and linked Slack tasks.

        Returns `(task_id, user_id)` pairs. The user id was already being
        selected and thrown away, so a shared message deleted both users' task
        rows but only ever purged one user's vectors (NUMA-142 P6).
        """
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT id, user_id FROM public.tasks WHERE external_ref = %s",
                    (f"slack:{ts}",),
                )
                task_rows = [
                    (str(r[0]), str(r[1]))
                    for r in (cur.fetchall() or []) if r and r[0] and r[1]
                ]
                cur.execute("DELETE FROM public.slack_messages WHERE ts = %s", (ts,))
                cur.execute(
                    "DELETE FROM public.tasks WHERE external_ref = %s",
                    (f"slack:{ts}",),
                )
                conn.commit()
                return task_rows
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
                    # Legacy duplicates only. `(user_id, external_ref)` is
                    # unique, so `external_ref = %s AND id <> %s` could never
                    # match a row; the clause read as if it swept same-ref
                    # duplicates and swept nothing (NUMA-142 P6).
                    cur.execute(
                        "DELETE FROM public.tasks "
                        "WHERE user_id = %s AND source_name = 'Slack' "
                        "  AND LOWER(title) = LOWER(%s) AND id <> %s "
                        "  AND external_ref IS NULL",
                        (user_id, title, task["id"]),
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
