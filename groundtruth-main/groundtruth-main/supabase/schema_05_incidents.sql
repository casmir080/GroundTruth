-- GroundTruth schema, step 5: agent-written incident reports for flagged calls.
-- Run this in Supabase -> SQL Editor (after schema_04_drift.sql).

create table if not exists public.incident_reports (
  call_id    uuid primary key references public.llm_calls(id) on delete cascade,
  verdict    text not null check (verdict in ('confirmed', 'false_positive', 'uncertain')),
  reasoning  text not null,
  report     text not null,
  created_at timestamptz not null default now()
);

alter table public.incident_reports enable row level security;
