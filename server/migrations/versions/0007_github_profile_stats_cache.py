"""github_profile_stats_cache

Revision ID: b3a6c1d94e57
Revises: e5c9b2d7f4a1
Create Date: 2026-09-06

The cached GitHub stats path, which is the default for every `/github/stats`
load, hardcoded followers, following and open PRs to 0 and derived repository
counts from `github_repositories`, whose cache query carries `LIMIT 8`. A user
with 50 repositories and 200 followers saw `public_repos: 8` and zeros
everywhere else on every page load; the real numbers appeared only after a
forced refresh and reverted on the next load (NUMA-142 P6, PLAN 7).

Nothing persisted the profile-level totals, so there was nothing for the cached
path to read. These two columns hold the totals from the last live fetch, and
the timestamp gives the cache the freshness bound it never had.
"""
from alembic import op


revision = "b3a6c1d94e57"
down_revision = "e5c9b2d7f4a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.github_auth "
        "ADD COLUMN IF NOT EXISTS profile_stats JSONB NOT NULL DEFAULT '{}'::JSONB"
    )
    op.execute(
        "ALTER TABLE public.github_auth "
        "ADD COLUMN IF NOT EXISTS profile_stats_synced_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS profile_stats_synced_at")
    op.execute("ALTER TABLE public.github_auth DROP COLUMN IF EXISTS profile_stats")
