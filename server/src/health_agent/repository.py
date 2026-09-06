"""Health data-access layer (NUMA-116, PLAN 6/18/21). SQL only.

The router keeps its wrapper functions (return-bool / swallow-to-None-or-[] /
log semantics); these methods run the raw SQL and raise on error so the wrappers
can preserve their exact behavior.
"""
from datetime import date, datetime
from typing import Dict, List, Optional

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict, using

_SNAPSHOT_COLS = (
    "id, user_id, source, snapshot_date, steps, active_minutes, "
    "calories, distance_km, sleep_hours, heart_rate_bpm, "
    "heart_points, sleep_start_at, sleep_end_at, "
    "sleep_stages, sleep_segments, activities, created_at, updated_at"
)


class HealthRepository(BaseRepository):
    def timezone_name(self, user_id: str) -> Optional[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT timezone FROM public.profiles WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def upsert_snapshot(
        self, user_id: str, source: str, snapshot_date: date,
        steps, active_minutes, calories, distance_km, sleep_hours,
        heart_rate_bpm, heart_points, sleep_start_at, sleep_end_at,
        sleep_stages, sleep_segments, activities,
    ) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.health_snapshots "
                    "(user_id, source, snapshot_date, steps, active_minutes, calories, "
                    " distance_km, sleep_hours, heart_rate_bpm, heart_points, "
                    " sleep_start_at, sleep_end_at, sleep_stages, sleep_segments, activities) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (user_id, source, snapshot_date) DO UPDATE SET "
                    "    steps = EXCLUDED.steps, "
                    "    active_minutes = EXCLUDED.active_minutes, "
                    "    calories = EXCLUDED.calories, "
                    "    distance_km = EXCLUDED.distance_km, "
                    "    sleep_hours = EXCLUDED.sleep_hours, "
                    "    heart_rate_bpm = EXCLUDED.heart_rate_bpm, "
                    "    heart_points = EXCLUDED.heart_points, "
                    "    sleep_start_at = EXCLUDED.sleep_start_at, "
                    "    sleep_end_at = EXCLUDED.sleep_end_at, "
                    "    sleep_stages = EXCLUDED.sleep_stages, "
                    "    sleep_segments = EXCLUDED.sleep_segments, "
                    "    activities = EXCLUDED.activities, "
                    "    updated_at = NOW()",
                    (
                        user_id, source, snapshot_date, steps, active_minutes, calories,
                        distance_km, sleep_hours, heart_rate_bpm, heart_points,
                        sleep_start_at, sleep_end_at, sleep_stages, sleep_segments, activities,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def delete_snapshot(self, user_id: str, source: str, snapshot_date: date) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "DELETE FROM public.health_snapshots "
                    "WHERE user_id = %s AND source = %s AND snapshot_date = %s",
                    (user_id, source, snapshot_date),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def upsert_intraday(
        self, user_id: str, source: str, snapshot_date: date,
        window_start_at: datetime, window_end_at: datetime, bucket_minutes: int,
        steps: int, calories: int, distance_km: float, buckets_json: str,
    ) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO public.health_intraday_snapshots "
                    "(user_id, source, snapshot_date, window_start_at, window_end_at, "
                    " bucket_minutes, steps, calories, distance_km, buckets) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (user_id, source, snapshot_date, bucket_minutes) DO UPDATE SET "
                    "    window_start_at = EXCLUDED.window_start_at, "
                    "    window_end_at = EXCLUDED.window_end_at, "
                    "    steps = EXCLUDED.steps, "
                    "    calories = EXCLUDED.calories, "
                    "    distance_km = EXCLUDED.distance_km, "
                    "    buckets = EXCLUDED.buckets, "
                    "    updated_at = NOW()",
                    (
                        user_id, source, snapshot_date, window_start_at, window_end_at,
                        bucket_minutes, steps, calories, distance_km, buckets_json,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_intraday(
        self, user_id: str, snapshot_date: date, source: str, bucket_minutes: int,
    ) -> Optional[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, user_id, source, snapshot_date, window_start_at, window_end_at, "
                "       bucket_minutes, steps, calories, distance_km, buckets, "
                "       created_at, updated_at "
                "FROM public.health_intraday_snapshots "
                "WHERE user_id = %s AND source = %s AND snapshot_date = %s "
                "  AND bucket_minutes = %s LIMIT 1",
                (user_id, source, snapshot_date, bucket_minutes),
            )
            row = cur.fetchone()
            return row_to_dict(cur, row) if row else None

    def get_snapshots(
        self, user_id: str, source: Optional[str], cutoff: date,
    ) -> List[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            if source:
                cur.execute(
                    "SELECT " + _SNAPSHOT_COLS + " FROM public.health_snapshots "
                    "WHERE user_id = %s AND source = %s AND snapshot_date >= %s "
                    "ORDER BY snapshot_date DESC",
                    (user_id, source, cutoff),
                )
            else:
                cur.execute(
                    "SELECT " + _SNAPSHOT_COLS + " FROM public.health_snapshots "
                    "WHERE user_id = %s AND snapshot_date >= %s "
                    "ORDER BY snapshot_date DESC",
                    (user_id, cutoff),
                )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    #: The metrics every caller of `day_metrics` reads, in one place. Four
    #: modules each selected their own subset with their own SQL, so the
    #: repository governed two of six read paths (NUMA-143 P7, PLAN 10).
    DAY_METRIC_COLS = (
        "source, steps, active_minutes, calories, distance_km, "
        "sleep_hours, heart_rate_bpm, heart_points"
    )

    def day_metrics(
        self, user_id: str, snapshot_date: date, *, conn=None,
    ) -> List[Dict]:
        """Every source's snapshot for one day.

        Takes an optional caller connection so a module batching statements on
        one connection can use this without opening a second - which is why the
        dashboard, journal, day planner and master agent each hand-rolled this
        query instead.
        """
        with using(conn) as active:
            cur = active.cursor()
            cur.execute(
                "SELECT " + self.DAY_METRIC_COLS + " FROM public.health_snapshots "
                "WHERE user_id = %s AND snapshot_date = %s",
                (user_id, snapshot_date),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def daily_totals_between(
        self, user_id: str, source: str, start: date, end: date, *, conn=None,
    ) -> List[Dict]:
        """One source's per-day totals across an inclusive date range."""
        with using(conn) as active:
            cur = active.cursor()
            cur.execute(
                "SELECT snapshot_date, steps, calories, distance_km "
                "FROM public.health_snapshots "
                "WHERE user_id = %s AND source = %s "
                "  AND snapshot_date >= %s AND snapshot_date <= %s "
                "ORDER BY snapshot_date",
                (user_id, source, start, end),
            )
            rows = cur.fetchall()
            return [row_to_dict(cur, r) for r in rows]

    def purge_older_than(self, cutoff: date) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "DELETE FROM public.health_snapshots WHERE snapshot_date < %s",
                    (cutoff,),
                )
                deleted = cur.rowcount
                cur.execute(
                    "DELETE FROM public.health_intraday_snapshots WHERE snapshot_date < %s",
                    (cutoff,),
                )
                deleted += cur.rowcount
                conn.commit()
                return deleted
            except Exception:
                conn.rollback()
                raise


health_repository = HealthRepository()
