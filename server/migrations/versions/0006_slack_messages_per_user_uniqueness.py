"""slack_messages_per_user_uniqueness

Revision ID: e5c9b2d7f4a1
Revises: d1f8a7c3e9b2
Create Date: 2026-09-06

`slack_messages.ts` was globally UNIQUE, but a Slack message belongs to a
workspace, not to one NUMA user. `_save_slack_message` fans a webhook out over
every NUMA user in the team and the writer upserts
`ON CONFLICT (ts) DO UPDATE SET user_id = EXCLUDED.user_id`, so with two users
in one workspace the second write took the row away from the first. Every read
filters `WHERE user_id = %s`, so the first user's messages, agent context and
task extraction silently went empty the moment a teammate connected
(NUMA-142 P6, PLAN 7).

Ownership moves to `(user_id, ts)`: one row per user per message. The no-user
fallback path still writes `user_id = NULL`, and Postgres treats NULLs as
distinct in a UNIQUE constraint, so that path would lose its dedup and insert a
fresh row on every redelivery. A partial unique index on `ts WHERE user_id IS
NULL` keeps exactly one unowned row per message, and gives the writer something
to name in its `ON CONFLICT`.
"""
from alembic import op


revision = "e5c9b2d7f4a1"
down_revision = "d1f8a7c3e9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop by lookup, not by name. The constraint came from an inline `UNIQUE`
    # in the baseline, which Postgres names `slack_messages_ts_key` by
    # convention - but a database first built from the old `sql/schema.sql`
    # could carry a different name, and a hardcoded DROP would fail there. This
    # finds whichever unique constraint covers exactly the `ts` column.
    op.execute("""
        DO $$
        DECLARE
            constraint_name TEXT;
        BEGIN
            SELECT con.conname INTO constraint_name
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = 'public'
              AND rel.relname = 'slack_messages'
              AND con.contype = 'u'
              AND (
                  SELECT array_agg(att.attname ORDER BY att.attname)
                  FROM unnest(con.conkey) AS k(attnum)
                  JOIN pg_attribute att
                    ON att.attrelid = con.conrelid AND att.attnum = k.attnum
              ) = ARRAY['ts']
            LIMIT 1;

            IF constraint_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE public.slack_messages DROP CONSTRAINT %I',
                    constraint_name
                );
            END IF;
        END $$;
    """)

    # No de-duplication step is needed on the way up: every existing row was
    # unique on `ts` alone, so it is trivially unique on `(user_id, ts)`.
    op.execute("""
        ALTER TABLE public.slack_messages
        ADD CONSTRAINT uq_slack_messages_user_ts UNIQUE (user_id, ts)
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_slack_messages_ts_unowned
        ON public.slack_messages (ts)
        WHERE user_id IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.uq_slack_messages_ts_unowned")
    op.execute("""
        ALTER TABLE public.slack_messages
        DROP CONSTRAINT IF EXISTS uq_slack_messages_user_ts
    """)

    # Going back to a global UNIQUE(ts) cannot be lossless: this migration's
    # whole point is that several rows may now share a ts. Keep the oldest row
    # per ts and drop the rest, which restores the shape the constraint needs.
    # The discarded rows are other users' copies of a message that is still in
    # Slack, so a re-sync rebuilds them for whichever single user wins.
    op.execute("""
        DELETE FROM public.slack_messages a
        USING public.slack_messages b
        WHERE a.ts = b.ts
          AND (a.created_at, a.id) > (b.created_at, b.id)
    """)

    op.execute("""
        ALTER TABLE public.slack_messages
        ADD CONSTRAINT slack_messages_ts_key UNIQUE (ts)
    """)
