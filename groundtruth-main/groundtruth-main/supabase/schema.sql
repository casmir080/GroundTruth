-- GroundTruth schema, step 1: log every LLM call.
-- Run this in Supabase -> SQL Editor.

create table if not exists public.llm_calls (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  source            text not null default 'live' check (source in ('live', 'benchmark')),
  query_type        text,
  prompt            text not null,
  response          text,
  model             text not null,
  model_version     text,
  latency_ms        integer,
  prompt_tokens     integer,
  completion_tokens integer,
  error             text,
  metadata          jsonb not null default '{}'::jsonb
);

create index if not exists llm_calls_created_at_idx on public.llm_calls (created_at desc);
create index if not exists llm_calls_source_idx on public.llm_calls (source, created_at desc);

-- Backend uses the service key (bypasses RLS). No policies = anon key can't read anything.
alter table public.llm_calls enable row level security;
