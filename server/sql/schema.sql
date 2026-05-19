-- ============================================================
-- NUMA - Supabase PostgreSQL Schema
-- Generated from server/src/db.py TABLES.
-- Run this in Supabase Dashboard -> SQL Editor if startup init fails.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.numa_schema_migrations (
    version          TEXT        PRIMARY KEY,
    checksum         TEXT        NOT NULL,
    statements_count INTEGER     NOT NULL,
    applied_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.set_updated_at()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$;

CREATE TABLE IF NOT EXISTS public.profiles (
        id           UUID        PRIMARY KEY
                                 REFERENCES auth.users(id) ON DELETE CASCADE,
        full_name    TEXT,
        avatar_url   TEXT,
        google_id    TEXT,
        timezone     TEXT        NOT NULL DEFAULT 'Asia/Kolkata',
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS google_id TEXT;

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata';

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_profiles_updated_at'
        ) THEN
            CREATE TRIGGER trg_profiles_updated_at
            BEFORE UPDATE ON public.profiles
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

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

ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS external_ref TEXT;

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
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_tasks_updated_at'
        ) THEN
            CREATE TRIGGER trg_tasks_updated_at
            BEFORE UPDATE ON public.tasks
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_tasks_user_status       ON public.tasks(user_id, status);

CREATE INDEX IF NOT EXISTS idx_tasks_completed         ON public.tasks(user_id, completed_at) WHERE completed_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_user_external_ref ON public.tasks(user_id, external_ref);

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
    );

ALTER TABLE public.cal_calendars ADD COLUMN IF NOT EXISTS calendar_type TEXT NOT NULL DEFAULT 'personal';

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_calendars_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_calendars_updated_at
            BEFORE UPDATE ON public.cal_calendars
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_cal_calendars_user         ON public.cal_calendars(user_id);

CREATE INDEX IF NOT EXISTS idx_cal_calendars_user_primary ON public.cal_calendars(user_id, is_primary);

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_events_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_events_updated_at
            BEFORE UPDATE ON public.cal_events
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_cal_events_user_start      ON public.cal_events(user_id, start_at);

CREATE INDEX IF NOT EXISTS idx_cal_events_calendar_start  ON public.cal_events(calendar_id, start_at);

CREATE INDEX IF NOT EXISTS idx_cal_events_active          ON public.cal_events(user_id, start_at) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cal_events_recurring       ON public.cal_events(recurring_event_id) WHERE recurring_event_id IS NOT NULL;

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_attendees_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_attendees_updated_at
            BEFORE UPDATE ON public.cal_attendees
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_cal_attendees_event          ON public.cal_attendees(event_id);

CREATE INDEX IF NOT EXISTS idx_cal_attendees_event_response ON public.cal_attendees(event_id, response_status);

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_cal_watch_channels_updated_at'
        ) THEN
            CREATE TRIGGER trg_cal_watch_channels_updated_at
            BEFORE UPDATE ON public.cal_watch_channels
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_cal_watch_user       ON public.cal_watch_channels(user_id);

CREATE INDEX IF NOT EXISTS idx_cal_watch_calendar   ON public.cal_watch_channels(calendar_id);

CREATE INDEX IF NOT EXISTS idx_cal_watch_status     ON public.cal_watch_channels(status);

CREATE INDEX IF NOT EXISTS idx_cal_watch_expires_at ON public.cal_watch_channels(expires_at) WHERE status = 'active';

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
    );

DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'google_calendar_events'
              AND column_name  = 'raw_event'
        ) THEN
            ALTER TABLE public.google_calendar_events DROP COLUMN raw_event;
        END IF;
    END $$;

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
    );

CREATE TABLE IF NOT EXISTS public.slack_channels (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        slack_id      TEXT        NOT NULL UNIQUE,
        name          TEXT,
        team_id       TEXT        NOT NULL,
        is_private    BOOLEAN     NOT NULL DEFAULT FALSE,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

CREATE INDEX IF NOT EXISTS idx_slack_channels_slack_id ON public.slack_channels(slack_id);

CREATE INDEX IF NOT EXISTS idx_slack_channels_team_id  ON public.slack_channels(team_id);

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
    );

CREATE INDEX IF NOT EXISTS idx_slack_messages_user       ON public.slack_messages(user_id);

CREATE INDEX IF NOT EXISTS idx_slack_messages_created_at ON public.slack_messages(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_slack_messages_channel    ON public.slack_messages(slack_channel_id);

CREATE INDEX IF NOT EXISTS idx_slack_messages_ts         ON public.slack_messages(ts);

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_slack_auth_updated_at'
        ) THEN
            CREATE TRIGGER trg_slack_auth_updated_at
            BEFORE UPDATE ON public.slack_auth
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_slack_auth_user_id ON public.slack_auth(user_id);

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
        sleep_stages    JSONB,
        activities      JSONB,
        raw_data        JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, source, snapshot_date)
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_health_snapshots_updated_at'
        ) THEN
            CREATE TRIGGER trg_health_snapshots_updated_at
            BEFORE UPDATE ON public.health_snapshots
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_health_snapshots_user_date   ON public.health_snapshots(user_id, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_health_snapshots_user_source ON public.health_snapshots(user_id, source, snapshot_date DESC);

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_user_ai_settings_updated_at'
        ) THEN
            CREATE TRIGGER trg_user_ai_settings_updated_at
            BEFORE UPDATE ON public.user_ai_settings
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_user_ai_settings_user ON public.user_ai_settings(user_id);

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_journal_entries_updated_at'
        ) THEN
            CREATE TRIGGER trg_journal_entries_updated_at
            BEFORE UPDATE ON public.journal_entries
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date ON public.journal_entries(user_id, entry_date DESC);

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
    );

ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_source TEXT;

ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_permissions JSONB NOT NULL DEFAULT '{}'::JSONB;

ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_last_verified_at TIMESTAMPTZ;

ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_auth_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_auth_updated_at
            BEFORE UPDATE ON public.github_auth
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_github_auth_user_id ON public.github_auth(user_id);

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
    );

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
    );

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
    );

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_repositories_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_repositories_updated_at
            BEFORE UPDATE ON public.github_repositories
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_commits_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_commits_updated_at
            BEFORE UPDATE ON public.github_commits
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_github_resource_snapshots_updated_at'
        ) THEN
            CREATE TRIGGER trg_github_resource_snapshots_updated_at
            BEFORE UPDATE ON public.github_resource_snapshots
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        END IF;
    END $$;

CREATE INDEX IF NOT EXISTS idx_github_repos_user_private ON public.github_repositories(user_id, private);

CREATE INDEX IF NOT EXISTS idx_github_repos_user_pushed ON public.github_repositories(user_id, pushed_at DESC);

CREATE INDEX IF NOT EXISTS idx_github_commits_user_time ON public.github_commits(user_id, committed_at DESC);

CREATE INDEX IF NOT EXISTS idx_github_commits_repo_time ON public.github_commits(user_id, repo_full_name, committed_at DESC);

CREATE INDEX IF NOT EXISTS idx_github_resources_user_type_time ON public.github_resource_snapshots(user_id, resource_type, occurred_at DESC);

INSERT INTO public.numa_schema_migrations
    (version, checksum, statements_count, applied_at)
VALUES
    (
        '2026_05_19_001',
        '16635830a7eb47a5b8b8745e7a7c9e09834ecd4b88906ec4fb0dfc9bba7a91fc',
        77,
        NOW()
    )
ON CONFLICT (version) DO UPDATE
SET checksum = EXCLUDED.checksum,
    statements_count = EXCLUDED.statements_count,
    applied_at = NOW();
