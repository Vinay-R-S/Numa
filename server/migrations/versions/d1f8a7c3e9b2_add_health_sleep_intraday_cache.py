"""add_health_sleep_intraday_cache

Revision ID: d1f8a7c3e9b2
Revises: c4e6f1a9d2b3
Create Date: 2026-05-24
"""
from alembic import op


revision = "d1f8a7c3e9b2"
down_revision = "c4e6f1a9d2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_start_at TIMESTAMPTZ")
    op.execute("ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_end_at TIMESTAMPTZ")
    op.execute("ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_segments JSONB")

    op.execute("""
        CREATE TABLE IF NOT EXISTS public.health_intraday_snapshots (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            source          TEXT        NOT NULL CHECK (source IN ('google_fit', 'strava')),
            snapshot_date   DATE        NOT NULL,
            window_start_at TIMESTAMPTZ NOT NULL,
            window_end_at   TIMESTAMPTZ NOT NULL,
            bucket_minutes  INTEGER     NOT NULL DEFAULT 60,
            steps           INTEGER     NOT NULL DEFAULT 0,
            calories        INTEGER     NOT NULL DEFAULT 0,
            distance_km     REAL        NOT NULL DEFAULT 0,
            buckets         JSONB       NOT NULL DEFAULT '[]'::JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, source, snapshot_date, bucket_minutes)
        )
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_health_intraday_snapshots_updated_at'
            ) THEN
                CREATE TRIGGER trg_health_intraday_snapshots_updated_at
                BEFORE UPDATE ON public.health_intraday_snapshots
                FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
            END IF;
        END $$
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_health_intraday_user_date "
        "ON public.health_intraday_snapshots(user_id, snapshot_date DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.health_intraday_snapshots")
    op.execute("ALTER TABLE public.health_snapshots DROP COLUMN IF EXISTS sleep_segments")
    op.execute("ALTER TABLE public.health_snapshots DROP COLUMN IF EXISTS sleep_end_at")
    op.execute("ALTER TABLE public.health_snapshots DROP COLUMN IF EXISTS sleep_start_at")
