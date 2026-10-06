"""Embed every logged response that doesn't have an embedding yet.

Usage (from backend/):
    python -m scripts.embed_calls
"""
from app.db import fetch_all, get_client
from app.embeddings import MODEL_NAME, embed

BATCH = 32


def main():
    db = get_client()

    # Fine up to ~1000 calls; paginate when the table grows past that.
    calls = fetch_all(
        lambda: db.table("llm_calls")
        .select("id, response")
        .filter("response", "not.is", "null")
        .order("created_at")
    )
    done = {r["call_id"] for r in fetch_all(lambda: db.table("call_embeddings").select("call_id"))}
    todo = [c for c in calls if c["id"] not in done]
    print(f"{len(calls)} responses, {len(todo)} to embed")

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        vecs = embed([c["response"] for c in batch])
        rows = [
            {"call_id": c["id"], "model": MODEL_NAME, "embedding": v}
            for c, v in zip(batch, vecs)
        ]
        db.table("call_embeddings").insert(rows).execute()
        print(f"embedded {min(i + BATCH, len(todo))}/{len(todo)}")

    print("done")


if __name__ == "__main__":
    main()
