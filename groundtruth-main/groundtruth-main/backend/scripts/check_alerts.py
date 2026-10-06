"""Check the latest drift snapshot and current hallucination flag rate
against thresholds; post to Slack if either is breached.

Meant to run right after psi_drift.py in the scheduled workflow -- this is
what turns "the data is sitting in a table" into "someone gets pinged."
Without SLACK_WEBHOOK_URL set, it just prints instead of posting.

Usage (from backend/):
    python -m scripts.check_alerts
"""
import json
import urllib.request

from app.config import settings
from app.db import fetch_all, get_client
from app.drift import SIGNIFICANT, psi_label

FLAG_RATE_ALERT = 0.40  # alert if >40% of recently scored calls are flagged


def notify(message: str) -> None:
    print(message)
    if not settings.slack_webhook_url:
        return
    body = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        settings.slack_webhook_url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"(failed to post to Slack: {e})")


def main():
    db = get_client()
    alerts = []

    latest_drift = (
        db.table("drift_snapshots").select("*").order("created_at", desc=True).limit(1).execute().data
    )
    if latest_drift:
        d = latest_drift[0]
        label = psi_label(d["psi"])
        print(f"latest drift: PSI={d['psi']:.4f} ({label}) [{d['baseline_run']} -> {d['current_run']}]")
        if d["psi"] >= SIGNIFICANT:
            alerts.append(
                f":rotating_light: GroundTruth: significant drift detected "
                f"(PSI={d['psi']:.3f}) between `{d['baseline_run']}` and `{d['current_run']}`."
            )

    recent_scores = fetch_all(
        lambda: db.table("hallucination_scores")
        .select("flagged")
        .order("created_at", desc=True)
    )[:100]
    if recent_scores:
        flag_rate = sum(r["flagged"] for r in recent_scores) / len(recent_scores)
        print(f"flag rate over last {len(recent_scores)} scored calls: {flag_rate:.1%}")
        if flag_rate >= FLAG_RATE_ALERT:
            alerts.append(
                f":rotating_light: GroundTruth: {flag_rate:.0%} of the last "
                f"{len(recent_scores)} scored calls were flagged as likely hallucinations "
                f"(alert threshold: {FLAG_RATE_ALERT:.0%})."
            )

    if alerts:
        for a in alerts:
            notify(a)
    else:
        print("nothing over threshold")


if __name__ == "__main__":
    main()
