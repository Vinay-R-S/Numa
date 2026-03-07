# Numa — Database Schema

All tables live in the `public` schema of the Supabase PostgreSQL instance.  
Tables are **auto-created** when the backend starts (`src/db.py` runs `CREATE TABLE IF NOT EXISTS`).  
Add new DDL to the `TABLES` list in `src/db.py` — it will be applied on next startup.

---

## Tables

### `public.profiles`

One row per user. Linked to Supabase's managed `auth.users` table via UUID foreign key.  
Created automatically on sign-up.

```sql
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID        PRIMARY KEY
                            REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name   TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` | PK — mirrors `auth.users.id` |
| `full_name` | `TEXT` | Display name (nullable) |
| `avatar_url` | `TEXT` | Profile picture URL (nullable) |
| `created_at` | `TIMESTAMPTZ` | Set on insert |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated via trigger |

---

## Functions & Triggers

### `public.set_updated_at()`

Keeps `updated_at` current on every row update (used by all tables that have the column).

```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;
```

### `trg_profiles_updated_at`

```sql
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

### `public.handle_new_user()` _(optional — belt-and-suspenders)_

Auto-creates a profile row whenever any new user is added to `auth.users`
(covers edge cases like direct Supabase Dashboard inserts).
The backend already upserts profiles via the API, so this is a fallback only.

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_on_new_user
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

---

## Relationships

```
auth.users (Supabase managed)
    │
    └── public.profiles   (1:1, ON DELETE CASCADE)
```

---

## How to apply manually (Supabase SQL Editor)

If auto-creation fails, paste the blocks above into  
**Supabase Dashboard → SQL Editor → New query** and run them in order:

1. `CREATE TABLE public.profiles …`
2. `CREATE OR REPLACE FUNCTION public.set_updated_at …`
3. `CREATE TRIGGER trg_profiles_updated_at …`

---

## Adding new tables

1. Write the `CREATE TABLE IF NOT EXISTS` SQL below in this file.
2. Add the same SQL string to the `TABLES` list in `server/src/db.py`.
3. Restart the backend — the table will be created automatically.

---

*Last updated: 2026-03-07*
