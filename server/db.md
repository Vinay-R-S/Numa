# Numa Database Schema

Numa uses Supabase PostgreSQL. Application tables live in the `public` schema and reference Supabase-managed `auth.users`.

Alembic is the single source of schema truth. All DDL lives in `server/migrations/versions/*.py`, ordered by numeric filename prefix:

```text
0001_baseline_schema.py                     # full base schema (tables, functions, triggers)
0002_add_indexes_triggers_deprecate_blobs.py
0003_expand_github_integration_cache.py
0004_add_health_heart_metrics.py
0005_add_health_sleep_intraday_cache.py
```

On backend startup, `init_db()` runs `alembic upgrade head`. On a clean database the baseline migration builds the full schema; on an existing database only pending migrations run. It is idempotent and safe to call on every startup.

You can run the same bootstrap manually from `server/`:

```powershell
.\.venv\Scripts\python.exe scripts\init_db.py
```

or invoke Alembic directly:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

## Changing the schema

1. Create a migration: `alembic revision -m "short_meaningful_name"`.
2. Rename the generated file with the next numeric prefix (e.g. `0006_short_meaningful_name.py`), keeping the `revision`/`down_revision` ids Alembic generated.
3. Write the DDL as `op.execute(...)` statements in `upgrade()`.
4. Apply with `alembic upgrade head` (or restart the backend).

Migration `revision` ids stay stable across renames because Alembic identifies migrations by the `revision` variable, not the filename. Existing databases stamped at a prior head keep resolving without a manual re-stamp.
