# Numa Database Schema

Numa uses Supabase PostgreSQL. Application tables live in the `public` schema and reference Supabase-managed `auth.users`.

The canonical schema is maintained in `server/src/db.py` as the `TABLES` list. On backend startup, `init_db()` creates `public.numa_schema_migrations`, checks the current schema version/checksum, verifies required tables exist, and only runs the idempotent schema statements when the database is missing or stale.

For manual Supabase setup, use:

```text
server/sql/schema.sql
```

Open **Supabase Dashboard -> SQL Editor -> New query**, paste the whole file, and run it. This is the file to use when startup logs show missing tables such as `public.profiles`, `public.tasks`, or `public.cal_calendars`.

You can also run the startup bootstrapper manually from `server/`:

```powershell
.\.venv\Scripts\python.exe scripts\init_db.py
```

## Keeping Schema In Sync

1. Update `TABLES` in `server/src/db.py`.
2. Bump `SCHEMA_VERSION` when the schema changes.
3. Regenerate `server/sql/schema.sql` from `TABLES`.
4. Restart the backend or run the SQL manually in Supabase.

The old task-only schema file was removed so there is one clear source for manual database setup.
