"""
Database initialization — runs CREATE TABLE IF NOT EXISTS on every startup.
Add new table DDL to the TABLES list to have them auto-created.
"""
import os
import logging
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
log = logging.getLogger(__name__)

# ── Connection helper ─────────────────────────────────────────────────────────

def _get_conn():
    """
    Parse DATABASE_URL manually to handle the '@' character inside the password.
    Format: postgresql://user:password@host:port/dbname
    """
    raw = os.environ["DATABASE_URL"].replace("postgresql://", "").replace("postgres://", "")

    # Split on the LAST '@' to separate credentials from host
    at = raw.rfind("@")
    credentials, host_part = raw[:at], raw[at + 1:]

    colon = credentials.find(":")
    user, password = credentials[:colon], credentials[colon + 1:]

    host_and_port, dbname = host_part.split("/", 1)
    if ":" in host_and_port:
        host, port = host_and_port.rsplit(":", 1)
    else:
        host, port = host_and_port, "5432"

    return psycopg2.connect(
        host=host,
        port=int(port),
        dbname=dbname,
        user=user,
        password=password,
        sslmode="require",
        connect_timeout=10,
    )


# ── Table definitions ─────────────────────────────────────────────────────────
# Add new CREATE TABLE IF NOT EXISTS blocks here as the app grows.

TABLES: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",

    # ── profiles ────────────────────────────────────────────────────────────
    # One row per user, linked to Supabase-managed auth.users via UUID FK.
    # Created automatically on sign-up (in auth service) or by the trigger below.
    """
    CREATE TABLE IF NOT EXISTS public.profiles (
        id          UUID        PRIMARY KEY
                                REFERENCES auth.users(id) ON DELETE CASCADE,
        full_name   TEXT,
        avatar_url  TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # Keep updated_at current on every row update
    """
    CREATE OR REPLACE FUNCTION public.set_updated_at()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_profiles_updated_at'
        ) THEN
            CREATE TRIGGER trg_profiles_updated_at
            BEFORE UPDATE ON public.profiles
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    # ── tasks ──────────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS public.tasks (
        id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        title        TEXT        NOT NULL,
        description  TEXT,
        status       TEXT        NOT NULL DEFAULT 'planned'
                                 CHECK (status IN ('planned', 'inprogress', 'completed', 'pending')),
        priority     TEXT        CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
        due_date     TIMESTAMPTZ,
        reminder_at  TIMESTAMPTZ,
        source_name  TEXT,
        source_logo  TEXT,
        external_ref TEXT,
        position     INTEGER     NOT NULL DEFAULT 0,
        completed_at TIMESTAMPTZ,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    "ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS external_ref TEXT",

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'uq_tasks_user_external_ref'
              AND conrelid = 'public.tasks'::regclass
        ) THEN
            ALTER TABLE public.tasks
            ADD CONSTRAINT uq_tasks_user_external_ref UNIQUE (user_id, external_ref);
        END IF;
    END $$
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_tasks_updated_at'
        ) THEN
            CREATE TRIGGER trg_tasks_updated_at
            BEFORE UPDATE ON public.tasks
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON public.tasks(user_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_completed   ON public.tasks(user_id, completed_at) WHERE completed_at IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_tasks_user_external_ref ON public.tasks(user_id, external_ref)",

    # ── google calendars ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS public.google_calendars (
        id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        google_calendar_id  TEXT        NOT NULL,
        summary             TEXT,
        description         TEXT,
        time_zone           TEXT,
        access_role         TEXT,
        selected            BOOLEAN     NOT NULL DEFAULT TRUE,
        is_primary          BOOLEAN     NOT NULL DEFAULT FALSE,
        raw_calendar        JSONB,
        last_synced_at      TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, google_calendar_id)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_google_calendars_updated_at'
        ) THEN
            CREATE TRIGGER trg_google_calendars_updated_at
            BEFORE UPDATE ON public.google_calendars
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_google_calendars_user ON public.google_calendars(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_google_calendars_user_selected ON public.google_calendars(user_id, selected)",

    # ── google calendar events snapshot ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS public.google_calendar_events (
        id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        google_calendar_id  TEXT        NOT NULL,
        google_event_id     TEXT        NOT NULL,
        ical_uid            TEXT,
        etag                TEXT,
        sequence            INTEGER,
        status              TEXT        CHECK (status IN ('confirmed', 'tentative', 'cancelled')),
        summary             TEXT        NOT NULL DEFAULT '(No title)',
        description         TEXT,
        location            TEXT,
        start_at            TIMESTAMPTZ NOT NULL,
        end_at              TIMESTAMPTZ NOT NULL,
        is_all_day          BOOLEAN     NOT NULL DEFAULT FALSE,
        start_time_zone     TEXT,
        end_time_zone       TEXT,
        html_link           TEXT,
        meet_link           TEXT,
        organizer           JSONB,
        creator             JSONB,
        attendees           JSONB       NOT NULL DEFAULT '[]'::JSONB,
        reminders           JSONB,
        raw_event           JSONB,
        is_readonly         BOOLEAN     NOT NULL DEFAULT FALSE,
        deleted_at          TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, google_calendar_id, google_event_id)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_google_calendar_events_updated_at'
        ) THEN
            CREATE TRIGGER trg_google_calendar_events_updated_at
            BEFORE UPDATE ON public.google_calendar_events
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_google_calendar_events_user_start ON public.google_calendar_events(user_id, start_at)",
    "CREATE INDEX IF NOT EXISTS idx_google_calendar_events_user_calendar_start ON public.google_calendar_events(user_id, google_calendar_id, start_at)",
    "CREATE INDEX IF NOT EXISTS idx_google_calendar_events_active ON public.google_calendar_events(user_id, deleted_at) WHERE deleted_at IS NULL",

    # ── google calendar sync/watch state ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS public.google_calendar_sync_state (
        id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id                UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        sync_scope             TEXT        NOT NULL DEFAULT 'incremental'
                                    CHECK (sync_scope IN ('full', 'incremental', 'watch')),
        next_sync_token        TEXT,
        last_sync_started_at   TIMESTAMPTZ,
        last_sync_completed_at TIMESTAMPTZ,
        last_sync_status       TEXT        CHECK (last_sync_status IN ('success', 'failed', 'running')),
        last_sync_error        TEXT,
        watch_channel_id       TEXT,
        watch_resource_id      TEXT,
        watch_expiration       TIMESTAMPTZ,
        watch_message_number   BIGINT,
        created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_google_calendar_sync_state_updated_at'
        ) THEN
            CREATE TRIGGER trg_google_calendar_sync_state_updated_at
            BEFORE UPDATE ON public.google_calendar_sync_state
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_google_calendar_sync_state_user ON public.google_calendar_sync_state(user_id)",
]


# ── Entrypoint ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Execute all DDL statements. Called once at application startup."""
    try:
        conn = _get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        for stmt in TABLES:
            cur.execute(stmt)
        cur.close()
        conn.close()
        log.info("✓ Database tables verified / created.")
    except Exception as exc:
        log.error("✗ Database init failed: %s", exc)
        # Non-fatal — app continues; fix the DB and restart
