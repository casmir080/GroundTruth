-- GroundTruth schema, step 4: PSI drift snapshots between two benchmark runs.
-- Run this in Supabase -> SQL Editor (after schema_03_hallucination.sql).

create table if not exists public.drift_snapshots (
  id             uuid primary key default gen_random_uuid(),
  created_at     timestamptz not null default now(),
  metric         text not null,             -- e.g. 'hallucination_score'
  baseline_run   text not null,
  current_run    text not null,
  psi            real not null,
  n_baseline     integer not null,
  n_current      integer not null,
  flagged        boolean not null           -- psi > 0.25 (industry-standard "significant shift" cutoff)
);

alter table public.drift_snapshots enable row level security;
