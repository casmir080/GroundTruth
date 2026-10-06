-- GroundTruth schema, step 3: hallucination score per benchmark call.
-- Run this in Supabase -> SQL Editor (after schema_02_embeddings.sql).
-- Only applies to benchmark calls, which carry reference answers in metadata.

create table if not exists public.hallucination_scores (
  call_id        uuid primary key references public.llm_calls(id) on delete cascade,
  sim_correct    real not null,   -- max similarity to any correct reference answer
  sim_incorrect  real not null,   -- max similarity to any incorrect reference answer
  score          real not null,   -- sim_correct - sim_incorrect; negative = likely hallucination
  flagged        boolean not null,
  created_at     timestamptz not null default now()
);

alter table public.hallucination_scores enable row level security;
