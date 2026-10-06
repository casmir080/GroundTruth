"""PSI drift check between two benchmark runs. Same technique used on
Watchtower for tabular features, applied here to the distribution of
hallucination scores across a run.

Usage (from backend/):
    python -m scripts.psi_drift BASELINE_RUN CURRENT_RUN
    python -m scripts.psi_drift              # auto: two most recent runs

Caveat: with only a handful of questions per run, PSI is noisy -- a single
score near a bin edge can flip the result either way. Treat readings below
--n 30 or so in load_benchmark.py as pipeline validation, not a verdict.
"""
import sys

from app.db import fetch_all, get_client
from app.drift import compute_psi, psi_label


def scores_for_run(db, run_id: str) -> list:
    calls = (
        db.table("llm_calls")
        .select("id")
        .eq("source", "benchmark")
        .eq("metadata->>run_id", run_id)
        .execute()
        .data
    )
    ids = [c["id"] for c in calls]
    if not ids:
        return []
    rows = db.table("hallucination_scores").select("call_id, score").in_("call_id", ids).execute().data
    return [r["score"] for r in rows]


def two_most_recent_runs(db) -> tuple:
    """Order distinct benchmark run_ids by their earliest call, return the
    two most recent as (baseline, current). Used by the scheduled workflow,
    which doesn't have a human around to type run IDs.
    """
    rows = fetch_all(
        lambda: db.table("llm_calls")
        .select("created_at, metadata")
        .eq("source", "benchmark")
        .order("created_at")
    )
    first_seen = {}
    for r in rows:
        run_id = (r["metadata"] or {}).get("run_id")
        if run_id and run_id not in first_seen:
            first_seen[run_id] = r["created_at"]
    ordered = sorted(first_seen, key=lambda k: first_seen[k])
    if len(ordered) < 2:
        return None, None
    return ordered[-2], ordered[-1]


def main():
    db = get_client()

    if len(sys.argv) == 3:
        baseline_run, current_run = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 1:
        baseline_run, current_run = two_most_recent_runs(db)
        if not baseline_run:
            print("fewer than 2 benchmark runs exist yet; nothing to compare")
            return
        print(f"auto-selected: baseline={baseline_run}  current={current_run}")
    else:
        print("usage: python -m scripts.psi_drift [BASELINE_RUN CURRENT_RUN]")
        return

    baseline = scores_for_run(db, baseline_run)
    current = scores_for_run(db, current_run)

    if len(baseline) < 4 or len(current) < 4:
        print(f"too few scored calls (baseline={len(baseline)}, current={len(current)}); "
              "need at least 4 each, run score_hallucination.py first")
        return

    value = compute_psi(baseline, current)
    label = psi_label(value)
    flagged = label == "significant"

    print(f"baseline={baseline_run} (n={len(baseline)})  current={current_run} (n={len(current)})")
    print(f"PSI = {value:.4f}  -> {label}")

    db.table("drift_snapshots").insert(
        {
            "metric": "hallucination_score",
            "baseline_run": baseline_run,
            "current_run": current_run,
            "psi": value,
            "n_baseline": len(baseline),
            "n_current": len(current),
            "flagged": flagged,
        }
    ).execute()


if __name__ == "__main__":
    main()
