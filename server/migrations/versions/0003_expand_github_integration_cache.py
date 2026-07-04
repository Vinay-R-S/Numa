"""expand_github_integration_cache

Revision ID: b9a1f3c8e2d4
Revises: 73d76abc6ad6
Create Date: 2026-05-19

Adds structured GitHub cache tables for repository and commit context, plus
token metadata needed for fine-grained/classic PAT permission tracking.
"""
from alembic import op


revision = "b9a1f3c8e2d4"
down_revision = "73d76abc6ad6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_source TEXT")
    op.execute("ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_permissions JSONB NOT NULL DEFAULT '{}'::JSONB")
    op.execute("ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_last_verified_at TIMESTAMPTZ")
    op.execute("ALTER TABLE public.github_auth ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ")

    op.execute("""
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
    """)

    op.execute("""
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
    """)

    op.execute("""
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
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_github_repositories_updated_at'
            ) THEN
                CREATE TRIGGER trg_github_repositories_updated_at
                BEFORE UPDATE ON public.github_repositories
                FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
            END IF;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_github_commits_updated_at'
            ) THEN
                CREATE TRIGGER trg_github_commits_updated_at
                BEFORE UPDATE ON public.github_commits
                FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
            END IF;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_github_resource_snapshots_updated_at'
            ) THEN
                CREATE TRIGGER trg_github_resource_snapshots_updated_at
                BEFORE UPDATE ON public.github_resource_snapshots
                FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
            END IF;
        END $$
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_github_repos_user_private ON public.github_repositories(user_id, private)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_repos_user_pushed ON public.github_repositories(user_id, pushed_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_commits_user_time ON public.github_commits(user_id, committed_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_commits_repo_time ON public.github_commits(user_id, repo_full_name, committed_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_resources_user_type_time ON public.github_resource_snapshots(user_id, resource_type, occurred_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.github_resource_snapshots")
    op.execute("DROP TABLE IF EXISTS public.github_commits")
    op.execute("DROP TABLE IF EXISTS public.github_repositories")
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS token_expires_at")
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS token_last_verified_at")
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS token_permissions")
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS token_source")
