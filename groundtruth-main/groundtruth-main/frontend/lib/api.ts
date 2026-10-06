const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DriftInfo = {
  psi: number;
  label: "none" | "moderate" | "significant";
  baseline_run: string;
  current_run: string;
} | null;

export type Status = { level: "stable" | "needs_review"; label: string };

export type Summary = {
  status: Status;
  total_calls: number;
  live_calls: number;
  benchmark_calls: number;
  flag_rate: number | null;
  flag_rate_sample_size: number;
  confirmed_rate: number | null;
  reviewed_count: number;
  drift: DriftInfo;
  total_cost_usd: number;
  incident_count: number;
};

export type DriftPoint = {
  psi: number;
  label: string;
  baseline_run: string;
  current_run: string;
  created_at: string;
  flagged: boolean;
};

export type Incident = {
  verdict: "confirmed" | "false_positive" | "uncertain";
  reasoning: string;
  report: string;
  created_at: string;
  question: string;
};

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null; // backend unreachable (asleep, not deployed yet, etc.) -- render empty state, don't crash
  }
}

export const getSummary = () => get<Summary>("/v1/dashboard/summary");
export const getDriftHistory = () => get<DriftPoint[]>("/v1/dashboard/drift-history");
export const getIncidents = () => get<Incident[]>("/v1/dashboard/incidents");
