"""Data retention: strip raw prompt/response text from llm_calls older than
a retention window, keeping the numeric scores (hallucination_scores,
drift_snapshots) intact for historical trend charts.

Rows are NOT deleted outright -- deleting would cascade and destroy the
scores too, losing history a dashboard trend line needs. Instead prompt/
response are nulled out, and the matching call_embeddings row is removed
since it's derived from the now-purged response text.

Usage (from backend/):
    python -m scripts.purge_old_calls --days 90
    python -m scripts.purge_old_calls --days 90 --dry-run
"""
import argparse
from datetime import datetime, timedelta, timezone

from app.db import fetch_all, get_client


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=90, help="retain raw text for this many days")
    p.add_argument("--dry-run", action="store_true", help="report what would change, change nothing")
    args = p.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    db = get_client()

    stale = fetch_all(
        lambda: db.table("llm_calls")
        .select("id")
        .lt("created_at", cutoff)
        .filter("prompt", "not.is", "null")  # not already purged
    )
    print(f"{len(stale)} calls older than {args.days} days with raw text still present")

    if args.dry_run or not stale:
        print("dry run -- nothing changed" if args.dry_run else "nothing to purge")
        return

    ids = [r["id"] for r in stale]
    for i in range(0, len(ids), 200):
        chunk = ids[i : i + 200]
        db.table("call_embeddings").delete().in_("call_id", chunk).execute()
        db.table("llm_calls").update({"prompt": None, "response": None}).in_("id", chunk).execute()
        print(f"purged {min(i + 200, len(ids))}/{len(ids)}")

    print("done")


if __name__ == "__main__":
    main()
