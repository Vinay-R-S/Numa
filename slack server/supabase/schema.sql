-- ============================================================
-- NUMA — Supabase PostgreSQL Schema
-- Run this in Supabase SQL Editor (Settings → SQL Editor → New query)
-- ============================================================

-- Enable the pgcrypto extension for UUID generation
create extension if not exists "pgcrypto";

-- Enable Row Level Security on every table

-- ──────────────────────────────────────────────────────────────
-- 1. USERS
-- ──────────────────────────────────────────────────────────────
create table if not exists public.users (
id            uuid primary key default gen_random_uuid(),
slack_user_id text unique not null,            -- e.g. U04XXXXXXX
slack_team_id text not null,                   -- e.g. T04XXXXXXX
display_name  text,
real_name     text,
email         text,
avatar_url    text,
timezone      text default 'UTC',
access_token  text,                            -- Slack OAuth bot token (encrypted at rest by Supabase Vault ideally)
created_at    timestamptz default now(),
updated_at    timestamptz default now()
);

alter table public.users enable row level security;

create policy "Users can read own record"
on public.users for select
using (auth.uid()::text = id::text);

create policy "Users can update own record"
on public.users for update
using (auth.uid()::text = id::text);

-- ──────────────────────────────────────────────────────────────
-- 2. MESSAGES  (raw Slack events captured by Slack Bolt)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.messages (
id            uuid primary key default gen_random_uuid(),
user_id       uuid references public.users(id) on delete cascade,
slack_user_id text not null,
slack_team_id text not null,
channel_id    text not null,
channel_name  text,
text          text,
ts            text unique not null,            -- Slack message timestamp (unique ID)
thread_ts     text,                            -- Null = not a thread reply
message_type  text default 'message',          -- message | command | reaction
  raw_payload   jsonb,                           -- full Slack event JSON
  created_at    timestamptz default now()
);

alter table public.messages enable row level security;

create policy "Users read own messages"
  on public.messages for select
  using (slack_user_id = (select slack_user_id from public.users where id = auth.uid()::uuid));

create index if not exists idx_messages_slack_user_id on public.messages(slack_user_id);
create index if not exists idx_messages_created_at    on public.messages(created_at desc);
create index if not exists idx_messages_channel_id    on public.messages(channel_id);

-- ──────────────────────────────────────────────────────────────
-- 3. TASKS
-- ──────────────────────────────────────────────────────────────
create table if not exists public.tasks (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references public.users(id) on delete cascade not null,
  title       text not null,
  description text,
  status      text default 'todo' check (status in ('todo','in_progress','done','cancelled')),
  priority    text default 'medium' check (priority in ('low','medium','high','urgent')),
  due_date    date,
  source      text default 'manual' check (source in ('manual','slack','ai')),
  slack_ts    text,                              -- reference to the message that created it
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

alter table public.tasks enable row level security;

create policy "Users manage own tasks"
  on public.tasks for all
  using (user_id = auth.uid()::uuid);

create index if not exists idx_tasks_user_id    on public.tasks(user_id);
create index if not exists idx_tasks_status     on public.tasks(status);
create index if not exists idx_tasks_due_date   on public.tasks(due_date);

-- ──────────────────────────────────────────────────────────────
-- 4. PLANS  (daily AI-generated schedule blocks)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.plans (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references public.users(id) on delete cascade not null,
  plan_date   date not null,
  blocks      jsonb not null default '[]',       -- [{label, start_time, end_time, tag}]
  summary     text,
  ai_model    text,
  created_at  timestamptz default now(),
  unique(user_id, plan_date)
);

alter table public.plans enable row level security;

create policy "Users manage own plans"
  on public.plans for all
  using (user_id = auth.uid()::uuid);

create index if not exists idx_plans_user_date on public.plans(user_id, plan_date desc);

-- ──────────────────────────────────────────────────────────────
-- 5. MOOD_LOGS
-- ──────────────────────────────────────────────────────────────
create table if not exists public.mood_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references public.users(id) on delete cascade not null,
  mood        text not null check (mood in ('great','good','okay','low','bad')),
  energy      int check (energy between 1 and 10),
  note        text,
  logged_at   timestamptz default now()
);

alter table public.mood_logs enable row level security;

create policy "Users manage own mood logs"
  on public.mood_logs for all
  using (user_id = auth.uid()::uuid);

create index if not exists idx_mood_user_date on public.mood_logs(user_id, logged_at desc);

-- ──────────────────────────────────────────────────────────────
-- 6. REFLECTIONS
-- ──────────────────────────────────────────────────────────────
create table if not exists public.reflections (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references public.users(id) on delete cascade not null,
  reflection_date date not null default current_date,
  what_went_well  text,
  what_to_improve text,
  gratitude       text,
  tomorrow_focus  text,
  ai_summary      text,
  created_at      timestamptz default now()
);

alter table public.reflections enable row level security;

create policy "Users manage own reflections"
  on public.reflections for all
  using (user_id = auth.uid()::uuid);

-- ──────────────────────────────────────────────────────────────
-- 7. NUDGES  (AI proactive suggestions / notifications)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.nudges (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references public.users(id) on delete cascade not null,
  type        text not null check (type in ('reminder','insight','suggestion','alert')),
  title       text not null,
  body        text,
  read        boolean default false,
  sent_via    text default 'app' check (sent_via in ('app','slack','email')),
  created_at  timestamptz default now()
);

alter table public.nudges enable row level security;

create policy "Users manage own nudges"
  on public.nudges for all
  using (user_id = auth.uid()::uuid);

create index if not exists idx_nudges_user_unread on public.nudges(user_id, read, created_at desc);

-- ──────────────────────────────────────────────────────────────
-- 8. ANALYTICS  (pre-aggregated daily scores)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.analytics (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid references public.users(id) on delete cascade not null,
  period_date         date not null,
  tasks_completed     int default 0,
  tasks_created       int default 0,
  messages_sent       int default 0,
  commands_used       int default 0,
  avg_mood            numeric(3,1),
  avg_energy          numeric(3,1),
  productivity_score  int,                -- 0–100
  focus_minutes       int default 0,
  created_at          timestamptz default now(),
  unique(user_id, period_date)
);

alter table public.analytics enable row level security;

create policy "Users read own analytics"
  on public.analytics for select
  using (user_id = auth.uid()::uuid);

create policy "Service role writes analytics"
  on public.analytics for insert
  with check (true);

create policy "Service role updates analytics"
  on public.analytics for update
  using (true);

create index if not exists idx_analytics_user_date on public.analytics(user_id, period_date desc);

-- ──────────────────────────────────────────────────────────────
-- 9. TRIGGER: auto-update updated_at timestamps
-- ──────────────────────────────────────────────────────────────
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger update_users_updated_at
  before update on public.users
  for each row execute function update_updated_at_column();

create trigger update_tasks_updated_at
  before update on public.tasks
  for each row execute function update_updated_at_column();

-- ──────────────────────────────────────────────────────────────
-- 10. Enable Realtime on key tables
-- ──────────────────────────────────────────────────────────────
-- Run in Supabase Dashboard → Database → Replication → Add table
-- Or via SQL:
alter publication supabase_realtime add table public.tasks;
alter publication supabase_realtime add table public.messages;
alter publication supabase_realtime add table public.nudges;
alter publication supabase_realtime add table public.mood_logs;
alter publication supabase_realtime add table public.plans;

-- ──────────────────────────────────────────────────────────────
-- 9. MONITOR STATE  (tracks last-fetched timestamp per channel)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.monitor_state (
  channel_id  text primary key,
  last_ts     text not null default '0',
  updated_at  timestamptz default now()
);

alter table public.monitor_state enable row level security;
-- Service role bypasses RLS; no user-facing policies needed.

-- ──────────────────────────────────────────────────────────────
-- 10. PROCESSED MESSAGES  (deduplication log for the monitor)
-- ──────────────────────────────────────────────────────────────
create table if not exists public.processed_messages (
  ts          text primary key,           -- Slack message timestamp
  created_at  timestamptz default now()
);

alter table public.processed_messages enable row level security;
-- Service role only.
