"""Score benchmark responses for groundedness against TruthfulQA's reference answers.

This is a semantic-similarity heuristic, not a true entailment model: a response
embeds close to "correct" reference answers and far from "incorrect" ones when it
agrees with them in meaning, not necessarily because it's factually verified.
Good enough to flag likely hallucinations for review; not a certified fact-checker.

Usage (from backend/):
    python -m scripts.score_hallucination
"""
import numpy as np

from app.db import fetch_all, get_client
from app.embeddings import embed
from app.hallucination import score as score_response


def main():
    db = get_client()

    calls = fetch_all(
        lambda: db.table("llm_calls")
        .select("id, response, metadata")
        .eq("source", "benchmark")
        .filter("response", "not.is", "null")
    )
    done = {r["call_id"] for r in fetch_all(lambda: db.table("hallucination_scores").select("call_id"))}
    todo = [c for c in calls if c["id"] not in done]
    print(f"{len(calls)} benchmark responses, {len(todo)} to score")

    for c in todo:
        meta = c["metadata"] or {}
        correct = meta.get("correct_answers") or []
        incorrect = meta.get("incorrect_answers") or []
        if not correct or not incorrect:
            continue

        resp_vec = np.array(embed([c["response"]])[0])
        correct_vecs = np.array(embed(correct))
        incorrect_vecs = np.array(embed(incorrect))
        result = score_response(resp_vec, correct_vecs, incorrect_vecs)

        db.table("hallucination_scores").insert(
            {
                "call_id": c["id"],
                "sim_correct": result["sim_correct"],
                "sim_incorrect": result["sim_incorrect"],
                "score": result["score"],
                "flagged": result["flagged"],
            }
        ).execute()
        flag = "FLAGGED" if result["flagged"] else "ok"
        print(f"{flag}  score={result['score']:+.3f}  {c['response'][:60]}")

    print("done")


if __name__ == "__main__":
    main()
