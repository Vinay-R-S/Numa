"""
Database initialization - runs CREATE TABLE IF NOT EXISTS on every startup.
Add new table DDL to the TABLES list to have them auto-created.
"""
import os
import hashlib
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
log = logging.getLogger(__name__)

# ── Connection pool ───────────────────────────────────────────────────────────
#
# All database operations share a process-wide connection pool instead of
# opening a fresh TCP connection on every call.  This eliminates the SSL
# handshake overhead and prevents connection exhaustion on Supabase.
#
# Existing code that calls ``_get_conn()`` / ``conn.close()`` continues to
# work unchanged — ``close()`` returns the connection to the pool rather
# than destroying it.  New code should prefer the ``get_db()`` context
# manager or call ``_put_conn(conn)`` in a finally block.

_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

_DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
_DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))


def _parse_database_url():
    """
    Parse DATABASE_URL manually to handle the '@' character inside the password.
    Format: postgresql://user:password@host:port/dbname
    """
    raw = os.environ["DATABASE_URL"].replace("postgresql://", "").replace("postgres://", "")

    at = raw.rfind("@")
    credentials, host_part = raw[:at], raw[at + 1:]

    colon = credentials.find(":")
    user, password = credentials[:colon], credentials[colon + 1:]

    host_and_port, dbname = host_part.split("/", 1)
    if ":" in host_and_port:
        host, port = host_and_port.rsplit(":", 1)
    else:
        host, port = host_and_port, "5432"

    return {
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
        "password": password,
        "sslmode": "require",
        "connect_timeout": 10,
    }


def _get_pool() -> ThreadedConnectionPool:
    """Return the process-wide connection pool, creating it on first call."""
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool

    with _pool_lock:
        # Double-check after acquiring lock
        if _pool is not None and not _pool.closed:
            return _pool

        params = _parse_database_url()
        _pool = ThreadedConnectionPool(
            minconn=_DB_POOL_MIN,
            maxconn=_DB_POOL_MAX,
            **params,
        )
        log.info(
            "✓ Database connection pool created (min=%d, max=%d, host=%s)",
            _DB_POOL_MIN, _DB_POOL_MAX, params["host"],
        )
        return _pool


class _PooledConnection:
    """
    Thin wrapper that makes ``conn.close()`` return the connection to the
    pool instead of destroying it.  This preserves backward compatibility
    with all existing code that does ``conn = _get_conn(); ... conn.close()``.
    """

    def __init__(self, real_conn, pool: ThreadedConnectionPool):
        object.__setattr__(self, "_conn", real_conn)
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_returned", False)

    def close(self):
        """Return connection to pool instead of closing it."""
        if not self._returned:
            self._returned = True
            try:
                # Reset connection state before returning to pool
                if not self._conn.closed:
                    self._conn.rollback()
                self._pool.putconn(self._conn)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name in {"_conn", "_pool", "_returned"}:
            object.__setattr__(self, name, value)
        else:
            setattr(self._conn, name, value)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _get_conn():
    """
    Get a database connection from the pool.

    The returned connection is wrapped so that calling ``.close()`` returns
    it to the pool rather than destroying it.  This makes this function a
    drop-in replacement for the old raw ``psycopg2.connect()`` call.
    """
    pool = _get_pool()
    real_conn = pool.getconn()
    return _PooledConnection(real_conn, pool)


def _put_conn(conn) -> None:
    """Explicitly return a pooled connection (alternative to conn.close())."""
    if isinstance(conn, _PooledConnection):
        conn.close()
    else:
        try:
            _get_pool().putconn(conn)
        except Exception:
            pass


@contextmanager
def get_db():
    """Context manager for database connections — recommended for new code.

    Usage::

        from src.db import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
    """
    conn = _get_conn()
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(cursor, row) -> dict:
    """Map a single DB row to a dict using the cursor description.

    Shared helper that replaces the per-feature _row_to_dict copies (PLAN 10).
    """
    if row is None:
        return {}
    cols = [c[0] for c in cursor.description]
    return dict(zip(cols, row))


# ── Table definitions ─────────────────────────────────────────────────────────
# Add new CREATE TABLE IF NOT EXISTS blocks here as the app grows.

TABLES: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",

    # ── shared updated_at trigger function ───────────────────────────────────
    """
    CREATE OR REPLACE FUNCTION public.set_updated_at()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$
    """,

    # ── profiles ─────────────────────────────────────────────────────────────
    # One row per user, linked to Supabase-managed auth.users via UUID FK.
    # Created automatically on sign-up (in auth service) or by the trigger below.
    """
    CREATE TABLE IF NOT EXISTS public.profiles (
        id           UUID        PRIMARY KEY
                                 REFERENCES auth.users(id) ON DELETE CASCADE,
        full_name    TEXT,
        avatar_url   TEXT,
        google_id    TEXT,
        timezone     TEXT        NOT NULL DEFAULT 'Asia/Kolkata',
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # Add new columns to profiles for existing deployments (idempotent)
    "ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS google_id TEXT",
    "ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata'",

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

    # ── tasks ─────────────────────────────────────────────────────────────────
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

    "CREATE INDEX IF NOT EXISTS idx_tasks_user_status       ON public.tasks(user_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_completed         ON public.tasks(user_id, completed_at) WHERE completed_at IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_tasks_user_external_ref ON public.tasks(user_id, external_ref)",

    # ═══════════════════════════════════════════════════════════════════════════
    # GOOGLE CALENDAR - NORMALIZED SCHEMA
    # ═══════════════════════════════════════════════════════════════════════════

    # ── cal_calendars ─────────────────────────────────────────────────────────
    # One row per Google calendar per user.
    # google_cal_id is the calendar's Google ID (e.g. primary or email address).
    # calendar_type drives frontend color-coding and agent filter logic.
    """
    CREATE TABLE IF NOT EXISTS public.cal_calendars (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        google_cal_id   TEXT        NOT NULL,
        name            TEXT        NOT NULL,
        access_role     TEXT        NOT NULL DEFAULT 'reader'
                                    CHECK (access_role IN ('owner', 'writer', 'reader', 'freeBusyReader')),
        is_primary      BOOLEAN     NOT NULL DEFAULT FALSE,
        calendar_type   TEXT        NOT NULL DEFAULT 'personal'
                                    CHECK (calendar_type IN ('personal', 'shared', 'holiday', 'birthday', 'other')),
        sync_token      TEXT,
        last_synced_at  TIMESTAMPTZ,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, google_cal_id)
    )
    """,

    # Add calendar_type to existing deployments (idempotent)
    "ALTER TABLE public.cal_calendars ADD COLUMN IF NOT EXISTS calendar_type TEXT NOT NULL DEFAULT 'personal'",

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_calendars_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_calendars_updated_at
            BEFORE UPDATE ON public.cal_calendars
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_cal_calendars_user         ON public.cal_calendars(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_cal_calendars_user_primary ON public.cal_calendars(user_id, is_primary)",

    # ── cal_events ────────────────────────────────────────────────────────────
    # One row per calendar event - no raw JSON blobs.
    # user_id is denormalized (redundant FK) for fast single-table range queries
    # without needing to join through cal_calendars.
    """
    CREATE TABLE IF NOT EXISTS public.cal_events (
        id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        calendar_id         UUID        NOT NULL REFERENCES public.cal_calendars(id) ON DELETE CASCADE,
        user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        google_event_id     TEXT        NOT NULL,
        title               TEXT        NOT NULL DEFAULT '(No title)',
        description         TEXT,
        location            TEXT,
        start_at            TIMESTAMPTZ NOT NULL,
        end_at              TIMESTAMPTZ NOT NULL,
        is_all_day          BOOLEAN     NOT NULL DEFAULT FALSE,
        start_time_zone     TEXT,
        end_time_zone       TEXT,
        status              TEXT        NOT NULL DEFAULT 'confirmed'
                                        CHECK (status IN ('confirmed', 'tentative', 'cancelled')),
        etag                TEXT,
        recurring_event_id  TEXT,
        html_link           TEXT,
        meet_link           TEXT,
        organizer_email     TEXT,
        organizer_name      TEXT,
        is_readonly         BOOLEAN     NOT NULL DEFAULT FALSE,
        deleted_at          TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (calendar_id, google_event_id)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_events_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_events_updated_at
            BEFORE UPDATE ON public.cal_events
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    # Indexes for common query patterns:
    # - range query for current month view
    # - fetch all events for a specific calendar
    # - recurring chain lookup
    "CREATE INDEX IF NOT EXISTS idx_cal_events_user_start      ON public.cal_events(user_id, start_at)",
    "CREATE INDEX IF NOT EXISTS idx_cal_events_calendar_start  ON public.cal_events(calendar_id, start_at)",
    "CREATE INDEX IF NOT EXISTS idx_cal_events_active          ON public.cal_events(user_id, start_at) WHERE deleted_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_cal_events_recurring       ON public.cal_events(recurring_event_id) WHERE recurring_event_id IS NOT NULL",

    # ── cal_attendees ─────────────────────────────────────────────────────────
    # One row per attendee per event.
    # Replaces the JSONB attendees blob that was stored in the old snapshot table.
    """
    CREATE TABLE IF NOT EXISTS public.cal_attendees (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id        UUID        NOT NULL REFERENCES public.cal_events(id) ON DELETE CASCADE,
        email           TEXT        NOT NULL,
        display_name    TEXT,
        response_status TEXT        NOT NULL DEFAULT 'needsAction'
                                    CHECK (response_status IN ('needsAction', 'accepted', 'declined', 'tentative')),
        is_organizer    BOOLEAN     NOT NULL DEFAULT FALSE,
        is_self         BOOLEAN     NOT NULL DEFAULT FALSE,
        optional        BOOLEAN     NOT NULL DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (event_id, email)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_attendees_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_attendees_updated_at
            BEFORE UPDATE ON public.cal_attendees
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_cal_attendees_event          ON public.cal_attendees(event_id)",
    "CREATE INDEX IF NOT EXISTS idx_cal_attendees_event_response ON public.cal_attendees(event_id, response_status)",

    # ── cal_watch_channels ────────────────────────────────────────────────────
    # Tracks Google Calendar push-notification channel registrations.
    # One channel per (user, calendar) pair; renewed before expiry.
    """
    CREATE TABLE IF NOT EXISTS public.cal_watch_channels (
        id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id              UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        calendar_id          UUID        NOT NULL REFERENCES public.cal_calendars(id) ON DELETE CASCADE,
        channel_uuid         TEXT        NOT NULL UNIQUE,
        google_resource_id   TEXT,
        status               TEXT        NOT NULL DEFAULT 'active'
                                         CHECK (status IN ('active', 'expired', 'stopped')),
        expires_at           TIMESTAMPTZ,
        registered_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_notification_at TIMESTAMPTZ,
        created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_watch_channels_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_watch_channels_updated_at
            BEFORE UPDATE ON public.cal_watch_channels
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_cal_watch_user       ON public.cal_watch_channels(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_cal_watch_calendar   ON public.cal_watch_channels(calendar_id)",
    "CREATE INDEX IF NOT EXISTS idx_cal_watch_status     ON public.cal_watch_channels(status)",
    "CREATE INDEX IF NOT EXISTS idx_cal_watch_expires_at ON public.cal_watch_channels(expires_at) WHERE status = 'active'",

    # ═══════════════════════════════════════════════════════════════════════════
    # LEGACY TABLES - kept for backward compatibility; no longer written to.
    # google_calendar_events.raw_event is dropped to free up storage.
    # ═══════════════════════════════════════════════════════════════════════════

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
        is_readonly         BOOLEAN     NOT NULL DEFAULT FALSE,
        deleted_at          TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, google_calendar_id, google_event_id)
    )
    """,

    # Drop the raw_event blob from the legacy table if it still exists
    """
    DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'google_calendar_events'
              AND column_name  = 'raw_event'
        ) THEN
            ALTER TABLE public.google_calendar_events DROP COLUMN raw_event;
        END IF;
    END $$
    """,

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

    # ═══════════════════════════════════════════════════════════════════════════
    # SLACK INTEGRATION
    # Rolling 7-day message window - old rows deleted nightly by scheduler.
    # Slack tasks reuse public.tasks with source_name='Slack'.
    # ═══════════════════════════════════════════════════════════════════════════

    # ── slack_channels ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS public.slack_channels (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        slack_id      TEXT        NOT NULL UNIQUE,
        name          TEXT,
        team_id       TEXT        NOT NULL,
        is_private    BOOLEAN     NOT NULL DEFAULT FALSE,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_slack_channels_slack_id ON public.slack_channels(slack_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_channels_team_id  ON public.slack_channels(team_id)",

    # ── slack_messages ────────────────────────────────────────────────────────
    # 7-day rolling window. Qdrant vectors share the same ts as payload key.
    """
    CREATE TABLE IF NOT EXISTS public.slack_messages (
        id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id          UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
        slack_user_id    TEXT        NOT NULL,
        slack_team_id    TEXT        NOT NULL,
        channel_id       UUID        REFERENCES public.slack_channels(id) ON DELETE SET NULL,
        slack_channel_id TEXT        NOT NULL,
        channel_name     TEXT,
        text             TEXT,
        ts               TEXT        NOT NULL UNIQUE,
        thread_ts        TEXT,
        message_type     TEXT        NOT NULL DEFAULT 'message',
        raw_payload      JSONB,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_slack_messages_user       ON public.slack_messages(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_messages_created_at ON public.slack_messages(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_slack_messages_channel    ON public.slack_messages(slack_channel_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_messages_ts         ON public.slack_messages(ts)",

    # ── slack_auth ────────────────────────────────────────────────────────────
    # One row per user - stores their Slack OAuth token.
    """
    CREATE TABLE IF NOT EXISTS public.slack_auth (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
        slack_user_id   TEXT        NOT NULL,
        slack_team_id   TEXT        NOT NULL,
        access_token    TEXT        NOT NULL,
        bot_token       TEXT,
        team_name       TEXT,
        authed_user_obj JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_slack_auth_updated_at'
        ) THEN
            CREATE TRIGGER trg_slack_auth_updated_at
            BEFORE UPDATE ON public.slack_auth
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_slack_auth_user_id ON public.slack_auth(user_id)",

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH INTEGRATION - Google Fit + Strava
    # Rolling 7+1 day window. Rows older than 8 days are purged daily at 8 AM.
    # One snapshot per user per day per source (google_fit / strava).
    # ═══════════════════════════════════════════════════════════════════════════

    """
    CREATE TABLE IF NOT EXISTS public.health_snapshots (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        source          TEXT        NOT NULL CHECK (source IN ('google_fit', 'strava')),
        snapshot_date   DATE        NOT NULL,
        steps           INTEGER,
        active_minutes  INTEGER,
        calories        INTEGER,
        distance_km     REAL,
        sleep_hours     REAL,
        heart_rate_bpm  REAL,
        heart_points    REAL,
        sleep_start_at  TIMESTAMPTZ,
        sleep_end_at    TIMESTAMPTZ,
        sleep_stages    JSONB,
        sleep_segments  JSONB,
        activities      JSONB,
        raw_data        JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, source, snapshot_date)
    )
    """,

    "ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS heart_rate_bpm REAL",
    "ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS heart_points REAL",
    "ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_start_at TIMESTAMPTZ",
    "ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_end_at TIMESTAMPTZ",
    "ALTER TABLE public.health_snapshots ADD COLUMN IF NOT EXISTS sleep_segments JSONB",

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_health_snapshots_updated_at'
        ) THEN
            CREATE TRIGGER trg_health_snapshots_updated_at
            BEFORE UPDATE ON public.health_snapshots
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_health_snapshots_user_date   ON public.health_snapshots(user_id, snapshot_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_health_snapshots_user_source ON public.health_snapshots(user_id, source, snapshot_date DESC)",

    """
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
    """,

    """
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
    """,

    "CREATE INDEX IF NOT EXISTS idx_health_intraday_user_date ON public.health_intraday_snapshots(user_id, snapshot_date DESC)",

    # ═══════════════════════════════════════════════════════════════════════════
    # USER AI SETTINGS - per-user LLM provider, model, encrypted API key
    # ═══════════════════════════════════════════════════════════════════════════

    """
    CREATE TABLE IF NOT EXISTS public.user_ai_settings (
        id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id           UUID        NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
        provider          TEXT        NOT NULL DEFAULT 'groq'
                                      CHECK (provider IN ('groq', 'openai', 'anthropic', 'gemini', 'ollama')),
        model_id          TEXT        NOT NULL DEFAULT 'llama-3.3-70b-versatile',
        encrypted_api_key TEXT,
        ollama_base_url   TEXT        DEFAULT 'http://localhost:11434',
        temperature       REAL        NOT NULL DEFAULT 0.1,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_user_ai_settings_updated_at'
        ) THEN
            CREATE TRIGGER trg_user_ai_settings_updated_at
            BEFORE UPDATE ON public.user_ai_settings
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_user_ai_settings_user ON public.user_ai_settings(user_id)",

    # ═══════════════════════════════════════════════════════════════════════════
    # JOURNAL ENTRIES - user daily journal / notes
    # ═══════════════════════════════════════════════════════════════════════════

    """
    CREATE TABLE IF NOT EXISTS public.journal_entries (
        id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        title       TEXT        NOT NULL DEFAULT '',
        content     TEXT        NOT NULL DEFAULT '',
        mood        TEXT        CHECK (mood IN ('great', 'good', 'okay', 'bad', 'terrible')),
        entry_date  DATE        NOT NULL DEFAULT CURRENT_DATE,
        tags        TEXT[]      DEFAULT '{}',
        ai_summary  TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, entry_date)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_journal_entries_updated_at'
        ) THEN
            CREATE TRIGGER trg_journal_entries_updated_at
            BEFORE UPDATE ON public.journal_entries
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date ON public.journal_entries(user_id, entry_date DESC)",

    # ═══════════════════════════════════════════════════════════════════════════
    # GITHUB INTEGRATION - OAuth token + cached contribution data
    # ═══════════════════════════════════════════════════════════════════════════

    """
    CREATE TABLE IF NOT EXISTS public.github_auth (
        id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id          UUID        NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
        github_username  TEXT        NOT NULL,
        github_user_id   INTEGER     NOT NULL,
        access_token     TEXT        NOT NULL,
        scope            TEXT,
        token_source     TEXT,
        token_permissions JSONB      NOT NULL DEFAULT '{}'::JSONB,
        token_last_verified_at TIMESTAMPTZ,
        token_expires_at TIMESTAMPTZ,
        avatar_url       TEXT,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    "ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_source TEXT",
    "ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_permissions JSONB NOT NULL DEFAULT '{}'::JSONB",
    "ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_last_verified_at TIMESTAMPTZ",
    "ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ",

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_auth_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_auth_updated_at
            BEFORE UPDATE ON public.github_auth
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_github_auth_user_id ON public.github_auth(user_id)",

    """
    CREATE TABLE IF NOT EXISTS public.github_repositories (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        github_repo_id  BIGINT,
        name            TEXT        NOT NULL,
        full_name       TEXT        NOT NULL,
        owner_login     TEXT,
        private         BOOLEAN     NOT NULL DEFAULT FALSE,
        fork            BOOLEAN     NOT NULL DEFAULT FALSE,
        archived        BOOLEAN     NOT NULL DEFAULT FALSE,
        disabled        BOOLEAN     NOT NULL DEFAULT FALSE,
        language        TEXT,
        stars           INTEGER     NOT NULL DEFAULT 0,
        forks           INTEGER     NOT NULL DEFAULT 0,
        open_issues     INTEGER     NOT NULL DEFAULT 0,
        default_branch  TEXT,
        html_url        TEXT,
        clone_url       TEXT,
        pushed_at       TIMESTAMPTZ,
        updated_at_api  TIMESTAMPTZ,
        permissions     JSONB       NOT NULL DEFAULT '{}'::JSONB,
        raw_payload     JSONB       NOT NULL DEFAULT '{}'::JSONB,
        last_synced_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, full_name)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS public.github_commits (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        repo_full_name  TEXT        NOT NULL,
        sha             TEXT        NOT NULL,
        message         TEXT        NOT NULL DEFAULT '',
        author_name     TEXT,
        author_email    TEXT,
        author_login    TEXT,
        committed_at    TIMESTAMPTZ,
        html_url        TEXT,
        raw_payload     JSONB       NOT NULL DEFAULT '{}'::JSONB,
        last_synced_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, repo_full_name, sha)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS public.github_resource_snapshots (
        id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        repo_full_name  TEXT,
        resource_type   TEXT        NOT NULL CHECK (
            resource_type IN (
                'pull_request',
                'issue',
                'action_run',
                'commit_status',
                'deployment',
                'discussion',
                'environment',
                'package',
                'page',
                'project',
                'security_event',
                'webhook'
            )
        ),
        external_id     TEXT        NOT NULL,
        title           TEXT,
        state           TEXT,
        html_url        TEXT,
        occurred_at     TIMESTAMPTZ,
        raw_payload     JSONB       NOT NULL DEFAULT '{}'::JSONB,
        last_synced_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, resource_type, external_id)
    )
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_repositories_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_repositories_updated_at
            BEFORE UPDATE ON public.github_repositories
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_commits_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_commits_updated_at
            BEFORE UPDATE ON public.github_commits
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_resource_snapshots_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_resource_snapshots_updated_at
            BEFORE UPDATE ON public.github_resource_snapshots
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$
    """,

    "CREATE INDEX IF NOT EXISTS idx_github_repos_user_private ON public.github_repositories(user_id, private)",
    "CREATE INDEX IF NOT EXISTS idx_github_repos_user_pushed ON public.github_repositories(user_id, pushed_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_github_commits_user_time ON public.github_commits(user_id, committed_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_github_commits_repo_time ON public.github_commits(user_id, repo_full_name, committed_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_github_resources_user_type_time ON public.github_resource_snapshots(user_id, resource_type, occurred_at DESC)",
]


SCHEMA_VERSION = "2026_05_24_001"

REQUIRED_TABLES = (
    "profiles",
    "tasks",
    "cal_calendars",
    "cal_events",
    "cal_attendees",
    "cal_watch_channels",
    "user_ai_settings",
    "journal_entries",
    "github_auth",
    "github_repositories",
    "github_commits",
    "github_resource_snapshots",
    "health_snapshots",
    "health_intraday_snapshots",
)

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS public.numa_schema_migrations (
    version          TEXT        PRIMARY KEY,
    checksum         TEXT        NOT NULL,
    statements_count INTEGER     NOT NULL,
    applied_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def _schema_checksum() -> str:
    normalized = "\n\n".join(" ".join(stmt.strip().split()) for stmt in TABLES)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _ensure_schema_migration_table(cur) -> None:
    cur.execute(SCHEMA_MIGRATIONS_DDL)


def _latest_schema_revision(cur) -> Optional[tuple[str, str, int]]:
    cur.execute(
        """
        SELECT version, checksum, statements_count
        FROM public.numa_schema_migrations
        ORDER BY applied_at DESC
        LIMIT 1
        """
    )
    return cur.fetchone()


def _missing_required_tables(cur) -> list[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(REQUIRED_TABLES),),
    )
    existing = {row[0] for row in cur.fetchall()}
    return [table for table in REQUIRED_TABLES if table not in existing]


def _record_schema_revision(cur, checksum: str) -> None:
    cur.execute(
        """
        INSERT INTO public.numa_schema_migrations
            (version, checksum, statements_count, applied_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (version) DO UPDATE
        SET checksum = EXCLUDED.checksum,
            statements_count = EXCLUDED.statements_count,
            applied_at = NOW()
        """,
        (SCHEMA_VERSION, checksum, len(TABLES)),
    )


def verify_required_tables() -> list[str]:
    """Return any required public tables that are still missing."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            return _missing_required_tables(cur)
        finally:
            cur.close()
    finally:
        conn.close()


# ── Entrypoint ────────────────────────────────────────────────────────────────

def init_db(*, raise_on_error: bool = False) -> None:
    """Create or migrate the database schema. Called once at application startup.

    The statements in TABLES are intentionally idempotent. Always executing
    them is safer than trusting only the schema_migrations row because it lets
    partially initialized databases repair themselves on the next startup.
    Existing tables are migrated with ALTER/CREATE IF NOT EXISTS statements;
    missing tables are created in the same pass.
    """
    current_stmt = ""
    conn = None
    cur = None
    try:
        checksum = _schema_checksum()
        conn = _get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        current_stmt = SCHEMA_MIGRATIONS_DDL
        _ensure_schema_migration_table(cur)

        latest = _latest_schema_revision(cur)
        missing_before = _missing_required_tables(cur)

        if latest is None:
            log.info("Database schema bootstrap needed; no migration record found.")
        elif missing_before:
            log.info(
                "Database schema repair needed; missing tables before migration: %s",
                ", ".join(missing_before),
            )
        elif latest[0] != SCHEMA_VERSION or latest[1] != checksum or latest[2] != len(TABLES):
            log.info(
                "Database schema migration needed; current=%s target=%s.",
                latest[0],
                SCHEMA_VERSION,
            )
        else:
            log.info("Database schema is current; verifying idempotent migrations anyway.")

        for stmt in TABLES:
            current_stmt = stmt
            cur.execute(stmt)

        missing_after = _missing_required_tables(cur)
        if missing_after:
            raise RuntimeError(
                "Database schema migration incomplete; missing tables: "
                + ", ".join(missing_after)
            )

        current_stmt = "INSERT INTO public.numa_schema_migrations"
        _record_schema_revision(cur, checksum)
        conn.commit()
        log.info("Database schema verified / migrated to %s.", SCHEMA_VERSION)
    except Exception:
        preview = " ".join(current_stmt.strip().split())[:240]
        message = (
            "Database init failed"
            + (f" while running: {preview}" if preview else " before any SQL ran")
        )
        log.exception(message)
        if raise_on_error:
            raise
        # Non-fatal when called manually without raise_on_error.
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
