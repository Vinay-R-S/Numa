"""
Database initialization — runs CREATE TABLE IF NOT EXISTS on every startup.
Add new table DDL to the TABLES list to have them auto-created.
"""
import os
import logging

import psycopg2
from dotenv import load_dotenv

load_dotenv()
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
        position     INTEGER     NOT NULL DEFAULT 0,
        completed_at TIMESTAMPTZ,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
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
