"""Run a fixed slice of TruthfulQA through the logged LLM wrapper.

Usage (from backend/):
    python -m scripts.load_benchmark --n 20
    python -m scripts.load_benchmark --n 20 --run-id week2

The shuffle seed is fixed, so the same --n gives the same questions every run.
That makes repeat runs comparable for drift. Each row's metadata keeps the
reference answers for the hallucination check later.
"""
import argparse
import time
from datetime import datetime, timezone

from datasets import load_dataset

from app.llm import logged_completion

SEED = 42


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--run-id", default=None)
    args = p.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ds = load_dataset("truthfulqa/truthful_qa", "generation", split="validation")
    ds = ds.shuffle(seed=SEED)
    n = min(args.n, len(ds))

    ok = failed = 0
    for i in range(n):
        row = ds[i]
        try:
            logged_completion(
                row["question"],
                source="benchmark",
                query_type=row["category"],
                metadata={
                    "dataset": "truthful_qa",
                    "question_idx": i,
                    "run_id": run_id,
                    "best_answer": row["best_answer"],
                    "correct_answers": row["correct_answers"],
                    "incorrect_answers": row["incorrect_answers"],
                },
            )
            ok += 1
        except Exception as e:
            failed += 1
            print(f"[{i + 1}/{n}] FAILED: {e}")
            continue
        print(f"[{i + 1}/{n}] {row['question'][:60]}")
        time.sleep(0.5)

    print(f"done. run_id={run_id} ok={ok} failed={failed}")


if __name__ == "__main__":
    main()
