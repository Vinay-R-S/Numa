"""Tasks data-access layer (NUMA-111, PLAN 6/18/21). SQL only, no business rules.

Extracted verbatim from tasks/router.py and tasks/service.py. Connection
lifecycle matches the previous inline code (get_db wraps the same pooled
_get_conn/close), so behavior is preserved.
"""
from datetime import datetime
from typing import Dict, List, Optional

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict

# Full column projection shared by every read/RETURNING clause. Constant, never
# interpolated with caller input, so this is not f-string SQL in the banned sense.
_COLS = (
    "id, user_id, title, description, status, priority, "
    "due_date, reminder_at, source_name, source_logo, "
    "external_ref, position, completed_at, created_at, updated_at"
)


class TaskRepository(BaseRepository):
    def list_active(self, user_id: str) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.tasks "
                "WHERE user_id = %s "
                "  AND (status != 'completed' "
                "       OR completed_at >= DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')) "
                "ORDER BY status, position ASC, created_at ASC",
                (user_id,),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def list_history(self, user_id: str) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.tasks "
                "WHERE user_id = %s "
                "  AND status = 'completed' "
                "  AND (completed_at IS NULL "
                "       OR completed_at < DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')) "
                "ORDER BY completed_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def insert(
        self,
        user_id: str,
        title: str,
        description: Optional[str],
        status: str,
        priority: Optional[str],
        due_date: Optional[datetime],
        reminder_at: Optional[datetime],
        source_name: Optional[str],
        source_logo: Optional[str],
        position: int,
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO public.tasks "
                "(user_id, title, description, status, priority, "
                " due_date, reminder_at, source_name, source_logo, position) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING " + _COLS,
                (
                    user_id, title, description, status, priority,
                    due_date, reminder_at, source_name, source_logo, position,
                ),
            )
            row = row_to_dict(cur, cur.fetchone())
            conn.commit()
            return row

    def get_sync_fields(self, task_id: str, user_id: str):
        """Return (external_ref, title, description, due_date) or None."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT external_ref, title, description, due_date "
                "FROM public.tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            return cur.fetchone()

    def update_partial(self, task_id: str, user_id: str, fields: Dict) -> Optional[Dict]:
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values())
        values.extend([task_id, user_id])
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE public.tasks SET " + set_clause + " "
                "WHERE id = %s AND user_id = %s "
                "RETURNING " + _COLS,
                values,
            )
            row = cur.fetchone()
            if not row:
                return None
            task = row_to_dict(cur, row)
            conn.commit()
            return task

    def update_status(
        self, task_id: str, user_id: str, status: str,
        completed_at: Optional[datetime], position: Optional[int],
    ) -> Optional[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE public.tasks "
                "SET status = %s, completed_at = %s, position = COALESCE(%s, position) "
                "WHERE id = %s AND user_id = %s "
                "RETURNING " + _COLS,
                (status, completed_at, position, task_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            task = row_to_dict(cur, row)
            conn.commit()
            return task

    def get_external_ref(self, task_id: str, user_id: str):
        """Return (external_ref,) row or None."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT external_ref FROM public.tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            return cur.fetchone()

    def delete(self, task_id: str, user_id: str) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM public.tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted

    # Analytics (GET /tasks/stats)
    def stats(self, user_id: str) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()

            cur.execute(
                "SELECT status, COUNT(*) FROM public.tasks WHERE user_id = %s GROUP BY status",
                (user_id,),
            )
            by_status = [{"status": r[0], "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT DATE(completed_at AT TIME ZONE 'UTC') as day, COUNT(*) "
                "FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "  AND completed_at >= NOW() - INTERVAL '30 days' "
                "GROUP BY day ORDER BY day",
                (user_id,),
            )
            daily = [{"date": str(r[0]), "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT DATE_TRUNC('week', completed_at AT TIME ZONE 'UTC') as week, COUNT(*) "
                "FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "  AND completed_at >= NOW() - INTERVAL '12 weeks' "
                "GROUP BY week ORDER BY week",
                (user_id,),
            )
            weekly = [{"date": str(r[0])[:10], "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT DATE_TRUNC('month', completed_at AT TIME ZONE 'UTC') as month, COUNT(*) "
                "FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "  AND completed_at >= NOW() - INTERVAL '12 months' "
                "GROUP BY month ORDER BY month",
                (user_id,),
            )
            monthly = [{"date": str(r[0])[:7], "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT EXTRACT(YEAR FROM completed_at AT TIME ZONE 'UTC')::int as year, COUNT(*) "
                "FROM public.tasks "
                "WHERE user_id = %s AND completed_at IS NOT NULL "
                "GROUP BY year ORDER BY year",
                (user_id,),
            )
            yearly = [{"date": str(r[0]), "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT COUNT(*) FROM public.tasks WHERE user_id = %s", (user_id,)
            )
            total = cur.fetchone()[0]

            cur.execute(
                "WITH daily_completions AS ("
                "    SELECT DISTINCT DATE(completed_at AT TIME ZONE 'UTC') as day "
                "    FROM public.tasks "
                "    WHERE user_id = %s AND completed_at IS NOT NULL"
                "), numbered AS ("
                "    SELECT day, "
                "           day - (ROW_NUMBER() OVER (ORDER BY day))::int * INTERVAL '1 day' AS grp "
                "    FROM daily_completions"
                ") SELECT COUNT(*) FROM numbered "
                "WHERE grp = ("
                "    SELECT day - (ROW_NUMBER() OVER (ORDER BY day))::int * INTERVAL '1 day' "
                "    FROM numbered WHERE day = CURRENT_DATE LIMIT 1"
                ")",
                (user_id,),
            )
            streak_row = cur.fetchone()
            streak = streak_row[0] if streak_row else 0

            return {
                "total": total,
                "by_status": by_status,
                "daily": daily,
                "weekly": weekly,
                "monthly": monthly,
                "yearly": yearly,
                "streak": streak,
            }

    # Agent / calendar-sync helpers (from tasks/service.py)
    def upsert_calendar_event_task(
        self, user_id: str, external_ref: str, title: str,
        description: Optional[str], due_date: Optional[datetime],
        reminder_at: Optional[datetime], source_name: str, source_logo: str,
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO public.tasks "
                "(user_id, title, description, status, due_date, reminder_at, "
                " source_name, source_logo, position, external_ref) "
                "VALUES (%s, %s, %s, 'planned', %s, %s, %s, %s, 0, %s) "
                "ON CONFLICT (user_id, external_ref) DO UPDATE SET "
                "    title = EXCLUDED.title, "
                "    description = EXCLUDED.description, "
                "    due_date = EXCLUDED.due_date, "
                "    reminder_at = EXCLUDED.reminder_at, "
                "    source_name = EXCLUDED.source_name, "
                "    source_logo = EXCLUDED.source_logo, "
                "    updated_at = NOW() "
                "RETURNING " + _COLS,
                (
                    user_id, title, description, due_date, reminder_at,
                    source_name, source_logo, external_ref,
                ),
            )
            task = row_to_dict(cur, cur.fetchone())
            conn.commit()
            return task

    def find_id_by_external_ref(self, user_id: str, external_ref: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM public.tasks "
                "WHERE user_id = %s AND external_ref = %s LIMIT 1",
                (user_id, external_ref),
            )
            return cur.fetchone()

    def delete_by_external_ref(self, user_id: str, external_ref: str) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM public.tasks WHERE user_id = %s AND external_ref = %s",
                (user_id, external_ref),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted

    def upsert_agent_task(
        self, user_id: str, title: str, description: Optional[str],
        status: str, due_date: Optional[datetime],
        source_name: Optional[str], source_logo: Optional[str], external_ref: str,
        priority: str = "medium",
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO public.tasks "
                "(user_id, title, description, status, priority, due_date, position, "
                " source_name, source_logo, external_ref) "
                "VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s) "
                "ON CONFLICT (user_id, external_ref) DO UPDATE SET "
                "    title = EXCLUDED.title, "
                "    description = EXCLUDED.description, "
                "    status = EXCLUDED.status, "
                # Priority is set on insert and then left alone: a re-run of the
                # day planner used to reset a priority the user had raised back
                # to the agent's default (NUMA-142 P6 review).
                "    due_date = EXCLUDED.due_date, "
                "    source_name = EXCLUDED.source_name, "
                "    source_logo = EXCLUDED.source_logo, "
                "    updated_at = NOW() "
                "RETURNING " + _COLS,
                (
                    user_id, title, description, status, priority, due_date,
                    source_name, source_logo, external_ref,
                ),
            )
            task = row_to_dict(cur, cur.fetchone())
            conn.commit()
            return task

    def find_id_by_title(self, user_id: str, title: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM public.tasks "
                "WHERE user_id = %s AND LOWER(title) = LOWER(%s) "
                "ORDER BY updated_at DESC LIMIT 1",
                (user_id, title),
            )
            return cur.fetchone()

    def get_by_id(self, task_id: str, user_id: str) -> Optional[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.tasks "
                "WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            row = cur.fetchone()
            return row_to_dict(cur, row) if row else None

    def update_by_id(self, task_id: str, user_id: str, updates: Dict) -> Optional[Dict]:
        """Alias of `update_partial`.

        It was a second copy of the same statement minus the missing-row check,
        so it returned `{}` where its own signature promised a task, and the
        agent path reported success for a task that did not exist
        (NUMA-142 P6, PLAN 10).
        """
        return self.update_partial(task_id, user_id, updates)

    def delete_latest_by_title(self, user_id: str, title: str) -> Optional[str]:
        """Delete the most recent task with this title and return its id.

        The caller used to find the id on one pooled connection and delete on
        another, so between the two a concurrent write could move the "latest"
        row and the vector cleanup ran against an id that was still live while
        the deleted one kept its vectors. One statement, one answer
        (NUMA-142 P6, PLAN 7).
        """
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM public.tasks WHERE id IN ("
                "    SELECT id FROM public.tasks "
                "    WHERE user_id = %s AND LOWER(title) = LOWER(%s) "
                "    ORDER BY updated_at DESC LIMIT 1"
                ") RETURNING id",
                (user_id, title),
            )
            row = cur.fetchone()
            conn.commit()
            return str(row[0]) if row else None

    def list_recent(self, user_id: str, limit: int = 10) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT " + _COLS + " FROM public.tasks "
                "WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, row) for row in rows]


task_repository = TaskRepository()
