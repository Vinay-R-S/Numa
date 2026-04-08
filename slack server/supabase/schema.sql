-- ============================================================
-- NUMA — Supabase PostgreSQL Schema (Current)
-- ============================================================

create extension if not exists "pgcrypto";

-- 1) users
create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  slack_user_id text not null unique,
  slack_team_id text not null,
  display_name text,
  real_name text,
  email text,
  avatar_url text,
  timezone text default 'UTC',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 2) user_tokens
create table if not exists public.user_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  access_token text not null,
  token_type text default 'bot',
  expires_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id)
);

-- 3) channels
create table if not exists public.channels (
  id uuid primary key default gen_random_uuid(),
  channel_id text not null unique,
  channel_name text,
  team_id text not null,
  is_private boolean default false,
  created_at timestamptz default now()
);

-- 4) messages
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id),
  slack_user_id text not null,
  slack_team_id text not null,
  channel_id text not null,
  channel_name text,
  text text,
  ts text not null unique,
  thread_ts text,
  message_type text default 'message',
  raw_payload jsonb,
  created_at timestamptz default now(),
  channel_uuid uuid references public.channels(id)
);

-- 5) tasks
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  title text not null,
  description text,
  status text default 'todo' check (status in ('todo','in_progress','done','cancelled')),
  priority text default 'medium' check (priority in ('low','medium','high','urgent')),
  due_date date,
  source text default 'manual' check (source in ('manual','slack','ai')),
  slack_ts text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 6) plans
create table if not exists public.plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  plan_date date not null,
  blocks jsonb not null default '[]'::jsonb,
  summary text,
  ai_model text,
  created_at timestamptz default now(),
  unique(user_id, plan_date)
);

-- 7) analytics
create table if not exists public.analytics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  period_date date not null,
  tasks_completed integer default 0,
  tasks_created integer default 0,
  messages_sent integer default 0,
  commands_used integer default 0,
  productivity_score integer,
  created_at timestamptz default now(),
  unique(user_id, period_date)
);

-- 8) nudges
create table if not exists public.nudges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  type text not null check (type in ('reminder','insight','suggestion','alert')),
  title text not null,
  body text,
  read boolean default false,
  sent_via text default 'app' check (sent_via in ('app','slack','email')),
  created_at timestamptz default now()
);

-- 9) monitor_state
create table if not exists public.monitor_state (
  channel_id text primary key,
  last_ts text not null default '0',
  updated_at timestamptz default now()
);

-- 10) processed_messages
create table if not exists public.processed_messages (
  ts text primary key,
  created_at timestamptz default now()
);

-- 11) extracted_intelligence
create table if not exists public.extracted_intelligence (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  type text not null,
  content text,
  metadata jsonb,
  source_date date,
  source_summary text,
  importance integer check (importance >= 1 and importance <= 10),
  embedding text,
  created_at timestamptz default now()
);

-- Indexes
create index if not exists idx_messages_slack_user_id on public.messages(slack_user_id);
create index if not exists idx_messages_created_at on public.messages(created_at desc);
create index if not exists idx_messages_channel_id on public.messages(channel_id);
create index if not exists idx_tasks_user_id on public.tasks(user_id);
create index if not exists idx_tasks_status on public.tasks(status);
create index if not exists idx_tasks_due_date on public.tasks(due_date);
create index if not exists idx_plans_user_date on public.plans(user_id, plan_date desc);
create index if not exists idx_analytics_user_date on public.analytics(user_id, period_date desc);
create index if not exists idx_nudges_user_read on public.nudges(user_id, read, created_at desc);

-- Trigger helper
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Triggers
create trigger update_users_updated_at
  before update on public.users
  for each row execute function update_updated_at_column();

create trigger update_tasks_updated_at
  before update on public.tasks
  for each row execute function update_updated_at_column();

create trigger update_user_tokens_updated_at
  before update on public.user_tokens
  for each row execute function update_updated_at_column();

-- Realtime publications
alter publication supabase_realtime add table public.tasks;
alter publication supabase_realtime add table public.messages;
alter publication supabase_realtime add table public.nudges;
alter publication supabase_realtime add table public.plans;
