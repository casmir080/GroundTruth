"""Compare two benchmark runs question by question.

Usage (from backend/):
    python -m scripts.compare_runs                 # list runs
    python -m scripts.compare_runs RUN_A RUN_B     # compare two runs

Similarity is cosine similarity between the two responses' embeddings
(1.0 = same meaning, lower = the answers differ more).
"""
import sys
from collections import Counter

import numpy as np

from app.db import get_client


def list_runs():
    rows = (
        get_client()
        .table("llm_calls")
        .select("metadata")
        .eq("source", "benchmark")
        .limit(1000)
        .execute()
        .data
    )
    counts = Counter(r["metadata"].get("run_id") for r in rows)
    for run_id, n in sorted(counts.items(), key=lambda x: str(x[0])):
        print(f"{run_id}  ({n} calls)")


def load_run(run_id):
    db = get_client()
    calls = (
        db.table("llm_calls")
        .select("id, prompt, metadata")
        .eq("source", "benchmark")
        .eq("metadata->>run_id", run_id)
        .execute()
        .data
    )
    by_id = {c["id"]: c for c in calls}
    ids = list(by_id)
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        embs = (
            db.table("call_embeddings")
            .select("call_id, embedding")
            .in_("call_id", chunk)
            .execute()
            .data
        )
        for e in embs:
            c = by_id[e["call_id"]]
            out[c["metadata"]["question_idx"]] = (
                c["prompt"],
                np.array(e["embedding"], dtype=float),
            )
    return out


def main():
    if len(sys.argv) != 3:
        list_runs()
        return

    a, b = load_run(sys.argv[1]), load_run(sys.argv[2])
    shared = sorted(set(a) & set(b))
    if not shared:
        print("No shared questions. Did you run embed_calls first?")
        return

    rows = []
    for idx in shared:
        prompt, va = a[idx]
        _, vb = b[idx]
        sim = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))
        rows.append((sim, idx, prompt))
    rows.sort()

    for sim, idx, prompt in rows:
        print(f"{sim:.3f}  [{idx}] {prompt[:60]}")

    sims = [r[0] for r in rows]
    print(f"\nquestions compared: {len(sims)}")
    print(f"mean similarity: {np.mean(sims):.3f}   min: {min(sims):.3f}")


if __name__ == "__main__":
    main()
