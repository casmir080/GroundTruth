-- GroundTruth schema, step 6: estimated cost per call.
-- Run this in Supabase -> SQL Editor (after schema_05_incidents.sql).

alter table public.llm_calls add column if not exists cost_usd numeric;
