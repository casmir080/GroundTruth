-- GroundTruth schema, step 2: one embedding per logged response.
-- Run this in Supabase -> SQL Editor (after schema.sql).

create table if not exists public.call_embeddings (
  call_id    uuid primary key references public.llm_calls(id) on delete cascade,
  model      text not null,
  embedding  real[] not null,
  created_at timestamptz not null default now()
);

alter table public.call_embeddings enable row level security;
