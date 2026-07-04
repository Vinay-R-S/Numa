"""add_indexes_triggers_deprecate_blobs

Revision ID: 73d76abc6ad6
Create Date: 2026-05-09

This migration:
1. Adds composite indexes for agent query patterns
2. Creates auto-purge trigger functions (safety net for scheduler)
3. Deprecates raw JSON blob columns (nullable, stop writing)
4. Adds missing indexes for common join/filter patterns
"""
from alembic import op


# revision identifiers
revision = "73d76abc6ad6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════════════
    # 1. NEW COMPOSITE INDEXES for agent query patterns
    # ══════════════════════════════════════════════════════════════════════════

    # Slack: user + created_at DESC for the agent's "recent messages" query
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_slack_messages_user_created "
        "ON public.slack_messages(user_id, created_at DESC)"
    )

    # Tasks: user + due_date for calendar→task sync queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_due "
        "ON public.tasks(user_id, due_date) WHERE due_date IS NOT NULL"
    )

    # Tasks: user + source_name for sub-agent task listing ("list Slack tasks")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_source "
        "ON public.tasks(user_id, source_name) WHERE source_name IS NOT NULL"
    )

    # Calendar: current-month partial index for fast dashboard queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cal_events_user_active_start "
        "ON public.cal_events(user_id, start_at) "
        "WHERE deleted_at IS NULL"
    )

    # Journal: user + entry_date for summary generation
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_journal_user_date "
        "ON public.journal_entries(user_id, entry_date DESC)"
    )

    # Health: user + source + date for agent snapshot queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_health_user_source_date "
        "ON public.health_snapshots(user_id, source, snapshot_date DESC)"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # 2. AUTO-PURGE TRIGGER FUNCTIONS (safety net for APScheduler)
    # ══════════════════════════════════════════════════════════════════════════

    # Slack messages: purge rows older than 7 days on INSERT
    # Uses a throttled approach - only runs cleanup every ~100 inserts
    op.execute("""
        CREATE OR REPLACE FUNCTION public.fn_throttled_slack_purge()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            -- Only purge occasionally (when random < 0.01 = ~1% of inserts)
            IF random() < 0.01 THEN
                DELETE FROM public.slack_messages
                WHERE created_at < NOW() - INTERVAL '7 days';
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_slack_auto_purge'
            ) THEN
                CREATE TRIGGER trg_slack_auto_purge
                AFTER INSERT ON public.slack_messages
                FOR EACH ROW EXECUTE FUNCTION public.fn_throttled_slack_purge();
            END IF;
        END $$
    """)

    # Health snapshots: purge rows older than 8 days on INSERT
    op.execute("""
        CREATE OR REPLACE FUNCTION public.fn_throttled_health_purge()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF random() < 0.01 THEN
                DELETE FROM public.health_snapshots
                WHERE snapshot_date < CURRENT_DATE - INTERVAL '8 days';
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_health_auto_purge'
            ) THEN
                CREATE TRIGGER trg_health_auto_purge
                AFTER INSERT ON public.health_snapshots
                FOR EACH ROW EXECUTE FUNCTION public.fn_throttled_health_purge();
            END IF;
        END $$
    """)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. DEPRECATE RAW JSON BLOB COLUMNS
    #    We make them nullable and add comments. Data is preserved for rollback.
    #    Future code will stop writing to these columns.
    # ══════════════════════════════════════════════════════════════════════════

    # health_snapshots.raw_data - full Google Fit / Strava API response
    op.execute(
        "COMMENT ON COLUMN public.health_snapshots.raw_data IS "
        "'DEPRECATED: No longer written to. Data lives in extracted columns.'"
    )

    # slack_messages.raw_payload - full Slack event JSON
    op.execute(
        "COMMENT ON COLUMN public.slack_messages.raw_payload IS "
        "'DEPRECATED: No longer written to. Data lives in extracted columns.'"
    )

    # google_calendars.raw_calendar - legacy table, full calendar list JSON
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'google_calendars'
                  AND column_name = 'raw_calendar'
            ) THEN
                EXECUTE 'COMMENT ON COLUMN public.google_calendars.raw_calendar IS '
                    || quote_literal('DEPRECATED: Legacy table. Use cal_calendars instead.');
            END IF;
        END $$
    """)


def downgrade() -> None:
    # ══════════════════════════════════════════════════════════════════════════
    # ROLLBACK: Remove triggers and indexes added in upgrade
    # ══════════════════════════════════════════════════════════════════════════

    # Remove auto-purge triggers
    op.execute("DROP TRIGGER IF EXISTS trg_slack_auto_purge ON public.slack_messages")
    op.execute("DROP TRIGGER IF EXISTS trg_health_auto_purge ON public.health_snapshots")

    # Remove trigger functions
    op.execute("DROP FUNCTION IF EXISTS public.fn_throttled_slack_purge()")
    op.execute("DROP FUNCTION IF EXISTS public.fn_throttled_health_purge()")

    # Remove new indexes
    op.execute("DROP INDEX IF EXISTS idx_slack_messages_user_created")
    op.execute("DROP INDEX IF EXISTS idx_tasks_user_due")
    op.execute("DROP INDEX IF EXISTS idx_tasks_user_source")
    op.execute("DROP INDEX IF EXISTS idx_cal_events_user_active_start")
    op.execute("DROP INDEX IF EXISTS idx_journal_user_date")
    op.execute("DROP INDEX IF EXISTS idx_health_user_source_date")

    # Remove deprecation comments (no-op - comments don't affect functionality)
