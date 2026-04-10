-- ============================================================
-- NUMA - Supabase PostgreSQL Schema
-- Run in Supabase Dashboard -> SQL Editor
-- ============================================================

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------
-- 1) Shared trigger function for updated_at
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- ------------------------------------------------------------
-- 2) Profiles table (used by auth service upsert)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name   TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_profiles_updated_at'
    ) THEN
        CREATE TRIGGER trg_profiles_updated_at
        BEFORE UPDATE ON public.profiles
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ------------------------------------------------------------
-- 3) Tasks table
-- ------------------------------------------------------------
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
);

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
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tasks_updated_at'
    ) THEN
        CREATE TRIGGER trg_tasks_updated_at
        BEFORE UPDATE ON public.tasks
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tasks_user_isolation" ON public.tasks;
CREATE POLICY "tasks_user_isolation"
    ON public.tasks FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ------------------------------------------------------------
-- 4) Indexes for task queries
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_user_status
    ON public.tasks(user_id, status);

CREATE INDEX IF NOT EXISTS idx_tasks_completed
    ON public.tasks(user_id, completed_at)
    WHERE completed_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_due_date
    ON public.tasks(user_id, due_date)
    WHERE due_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_created_at
    ON public.tasks(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_user_external_ref
    ON public.tasks(user_id, external_ref);

-- ------------------------------------------------------------
-- 5) Google Calendar metadata per user
-- ------------------------------------------------------------
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
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_google_calendars_updated_at'
    ) THEN
        CREATE TRIGGER trg_google_calendars_updated_at
        BEFORE UPDATE ON public.google_calendars
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

ALTER TABLE public.google_calendars ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "google_calendars_user_isolation" ON public.google_calendars;
CREATE POLICY "google_calendars_user_isolation"
    ON public.google_calendars FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_google_calendars_user
    ON public.google_calendars(user_id);

CREATE INDEX IF NOT EXISTS idx_google_calendars_user_selected
    ON public.google_calendars(user_id, selected);

-- ------------------------------------------------------------
-- 6) Google Calendar events cache per user
-- ------------------------------------------------------------
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
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_google_calendar_events_updated_at'
    ) THEN
        CREATE TRIGGER trg_google_calendar_events_updated_at
        BEFORE UPDATE ON public.google_calendar_events
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

ALTER TABLE public.google_calendar_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "google_calendar_events_user_isolation" ON public.google_calendar_events;
CREATE POLICY "google_calendar_events_user_isolation"
    ON public.google_calendar_events FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_google_calendar_events_user_start
    ON public.google_calendar_events(user_id, start_at);

CREATE INDEX IF NOT EXISTS idx_google_calendar_events_user_calendar_start
    ON public.google_calendar_events(user_id, google_calendar_id, start_at);

CREATE INDEX IF NOT EXISTS idx_google_calendar_events_active
    ON public.google_calendar_events(user_id, deleted_at)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------
-- 7) Google Calendar sync and watch state
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.google_calendar_sync_state (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sync_scope           TEXT        NOT NULL DEFAULT 'incremental'
                                  CHECK (sync_scope IN ('full', 'incremental', 'watch')),
    next_sync_token      TEXT,
    last_sync_started_at TIMESTAMPTZ,
    last_sync_completed_at TIMESTAMPTZ,
    last_sync_status     TEXT        CHECK (last_sync_status IN ('success', 'failed', 'running')),
    last_sync_error      TEXT,
    watch_channel_id     TEXT,
    watch_resource_id    TEXT,
    watch_expiration     TIMESTAMPTZ,
    watch_message_number BIGINT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_google_calendar_sync_state_updated_at'
    ) THEN
        CREATE TRIGGER trg_google_calendar_sync_state_updated_at
        BEFORE UPDATE ON public.google_calendar_sync_state
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

ALTER TABLE public.google_calendar_sync_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "google_calendar_sync_state_user_isolation" ON public.google_calendar_sync_state;
CREATE POLICY "google_calendar_sync_state_user_isolation"
    ON public.google_calendar_sync_state FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_google_calendar_sync_state_user
    ON public.google_calendar_sync_state(user_id);
