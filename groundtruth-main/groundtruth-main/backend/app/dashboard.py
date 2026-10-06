"""Public, read-only endpoints for the dashboard.

Deliberately separate from main.py's authenticated routes: these expose
only aggregates and already-public benchmark data, never raw live-traffic
prompts/responses. That split matters -- a public status page showing
someone's real prompt would be a privacy problem the moment live traffic
starts flowing through this thing, so incidents here are filtered to
source='benchmark' on purpose, not by accident.
"""
from fastapi import APIRouter

from .db import fetch_all, get_client
from .drift import psi_label

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary():
    db = get_client()

    def count(source: str = None) -> int:
        q = db.table("llm_calls").select("id", count="exact")
        if source:
            q = q.eq("source", source)
        return q.limit(1).execute().count

    recent_scores = fetch_all(
        lambda: db.table("hallucination_scores").select("flagged").order("created_at", desc=True)
    )[:100]
    flag_rate = (
        sum(r["flagged"] for r in recent_scores) / len(recent_scores) if recent_scores else None
    )

    latest_drift = (
        db.table("drift_snapshots").select("*").order("created_at", desc=True).limit(1).execute().data
    )
    drift = None
    if latest_drift:
        d = latest_drift[0]
        drift = {
            "psi": d["psi"],
            "label": psi_label(d["psi"]),
            "baseline_run": d["baseline_run"],
            "current_run": d["current_run"],
        }

    cost_rows = fetch_all(lambda: db.table("llm_calls").select("cost_usd").filter("cost_usd", "not.is", "null"))
    total_cost = sum(r["cost_usd"] for r in cost_rows)

    reports = fetch_all(lambda: db.table("incident_reports").select("verdict"))
    incident_count = len(reports)
    reviewed_count = sum(1 for r in reports if r["verdict"] in ("confirmed", "false_positive"))
    confirmed_count = sum(1 for r in reports if r["verdict"] == "confirmed")
    # Precision of the cheap heuristic, not "% of all answers that are wrong" --
    # only flagged calls get reviewed, so this only speaks to flagged ones.
    confirmed_rate = confirmed_count / reviewed_count if reviewed_count else None

    # Status is driven by DRIFT specifically -- whether behavior is changing
    # over time -- not by confirmed_rate's absolute value. TruthfulQA is built
    # from commonly-misunderstood questions on purpose, so some nonzero
    # confirmed-wrong rate is expected baseline difficulty, not a sign of
    # active degradation. Conflating "is this hard" with "is this changing"
    # would make the status alarm on normal benchmark behavior.
    if drift is not None and drift["label"] == "significant":
        status = {"level": "needs_review", "label": "Needs review"}
    else:
        status = {"level": "stable", "label": "Stable"}

    return {
        "status": status,
        "total_calls": count(),
        "live_calls": count("live"),
        "benchmark_calls": count("benchmark"),
        "flag_rate": flag_rate,
        "flag_rate_sample_size": len(recent_scores),
        "confirmed_rate": confirmed_rate,
        "reviewed_count": reviewed_count,
        "drift": drift,
        "total_cost_usd": round(total_cost, 6),
        "incident_count": incident_count,
    }


@router.get("/drift-history")
def drift_history(limit: int = 50):
    db = get_client()
    rows = (
        db.table("drift_snapshots")
        .select("psi, baseline_run, current_run, created_at, flagged")
        .order("created_at")
        .limit(min(limit, 200))
        .execute()
        .data
    )
    return [{**r, "label": psi_label(r["psi"])} for r in rows]


@router.get("/incidents")
def incidents(limit: int = 30):
    db = get_client()
    reports = (
        db.table("incident_reports")
        .select("call_id, verdict, reasoning, report, created_at")
        .order("created_at", desc=True)
        .limit(min(limit, 100))
        .execute()
        .data
    )
    if not reports:
        return []

    calls = (
        db.table("llm_calls")
        .select("id, prompt, source")
        .in_("id", [r["call_id"] for r in reports])
        .eq("source", "benchmark")  # public data only -- never surface live prompts here
        .execute()
        .data
    )
    prompt_by_id = {c["id"]: c["prompt"] for c in calls}

    return [
        {
            "verdict": r["verdict"],
            "reasoning": r["reasoning"],
            "report": r["report"],
            "created_at": r["created_at"],
            "question": prompt_by_id.get(r["call_id"]),
        }
        for r in reports
        if r["call_id"] in prompt_by_id
    ]