"""Journal data-access layer (NUMA-112, PLAN 6/18/21). SQL only."""
from datetime import date
from typing import Dict, List, Optional

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict

_COLS = (
    "id, user_id, title, content, mood, entry_date, tags, ai_summary, "
    "created_at, updated_at"
)

_UPSERT = (
    "INSERT INTO public.journal_entries "
    "(user_id, title, content, mood, entry_date, tags) "
    "VALUES (%s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (user_id, entry_date) DO UPDATE SET "
    "    title = EXCLUDED.title, "
    "    content = EXCLUDED.content, "
    "    mood = EXCLUDED.mood, "
    "    tags = EXCLUDED.tags, "
    "    updated_at = NOW() "
    "RETURNING " + _COLS
)


class JournalRepository(BaseRepository):
    def count(self, user_id: str) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM public.journal_entries WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()[0]

    def list(self, user_id: str, limit: int, offset: int) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.journal_entries "
                "WHERE user_id = %s ORDER BY entry_date DESC LIMIT %s OFFSET %s",
                (user_id, limit, offset),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def get(self, user_id: str, entry_date: date) -> Optional[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.journal_entries "
                "WHERE user_id = %s AND entry_date = %s",
                (user_id, entry_date),
            )
            row = cur.fetchone()
            return row_to_dict(cur, row) if row else None

    def upsert(
        self, user_id: str, title: str, content: str, mood: Optional[str],
        entry_date: date, tags: list,
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(_UPSERT, (user_id, title, content, mood, entry_date, tags))
                entry = row_to_dict(cur, cur.fetchone())
                conn.commit()
                return entry
            except Exception:
                conn.rollback()
                raise

    def update_fields(self, user_id: str, entry_date: date, fields: Dict) -> Optional[Dict]:
        set_clause = ", ".join(f"{k} = %s" for k in fields) + ", updated_at = NOW()"
        params = list(fields.values())
        params.extend([user_id, entry_date])
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE public.journal_entries SET " + set_clause + " "
                    "WHERE user_id = %s AND entry_date = %s "
                    "RETURNING " + _COLS,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    return None
                entry = row_to_dict(cur, row)
                conn.commit()
                return entry
            except Exception:
                conn.rollback()
                raise

    def delete(self, user_id: str, entry_date: date) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM public.journal_entries WHERE user_id = %s AND entry_date = %s",
                (user_id, entry_date),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted

    def set_summary(self, user_id: str, entry_date: date, summary: str) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE public.journal_entries "
                    "SET ai_summary = %s, updated_at = NOW() "
                    "WHERE user_id = %s AND entry_date = %s",
                    (summary, user_id, entry_date),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ── Raw reads for the daily-summary / auto-generate service ───────────────
    # These return raw rows (positional) to match the service's unpacking, and
    # do not swallow errors; the service keeps the same try/except it had.
    def content_row(self, user_id: str, target_date: date):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT title, content, mood, tags FROM public.journal_entries "
                "WHERE user_id = %s AND entry_date = %s",
                (user_id, target_date),
            )
            return cur.fetchone()

    def calendar_events(self, user_id: str, start, end) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT title, start_at, end_at FROM public.cal_events "
                "WHERE user_id = %s AND start_at >= %s AND start_at < %s AND deleted_at IS NULL "
                "ORDER BY start_at LIMIT 15",
                (user_id, start, end),
            )
            return cur.fetchall()

    def completed_tasks(self, user_id: str, start, end) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT title, status FROM public.tasks "
                "WHERE user_id = %s AND completed_at >= %s AND completed_at < %s "
                "ORDER BY completed_at LIMIT 20",
                (user_id, start, end),
            )
            return cur.fetchall()

    def health_rows(self, user_id: str, target_date: date) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT source, steps, active_minutes, calories, distance_km, sleep_hours, "
                "       heart_rate_bpm, heart_points "
                "FROM public.health_snapshots WHERE user_id = %s AND snapshot_date = %s",
                (user_id, target_date),
            )
            return cur.fetchall()

    def slack_highlights(self, user_id: str, start, end) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT channel_name, sender_name, text FROM public.slack_messages "
                "WHERE user_id = %s AND ("
                "    (created_at >= %s AND created_at < %s) "
                "    OR (ts ~ '^[0-9]+(\\.[0-9]+)?$' "
                "        AND to_timestamp(ts::double precision) >= %s "
                "        AND to_timestamp(ts::double precision) < %s)"
                ") ORDER BY created_at DESC LIMIT 15",
                (user_id, start, end, start, end),
            )
            return cur.fetchall()

    def github_username(self, user_id: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT github_username FROM public.github_auth WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()

    def github_commits(self, user_id: str, start, end) -> list:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT repo_full_name, message FROM public.github_commits "
                "WHERE user_id = %s AND committed_at >= %s AND committed_at < %s "
                "ORDER BY committed_at DESC LIMIT 10",
                (user_id, start, end),
            )
            return cur.fetchall()


journal_repository = JournalRepository()
