"""Run the verify -> synthesize agent pipeline over flagged calls that don't
have an incident report yet.

Usage (from backend/):
    python -m scripts.run_agents
"""
from app.agents import build_graph
from app.db import fetch_all, get_client


def main():
    db = get_client()
    graph = build_graph()

    flagged = fetch_all(
        lambda: db.table("hallucination_scores").select("call_id, score").eq("flagged", True)
    )
    done = {r["call_id"] for r in fetch_all(lambda: db.table("incident_reports").select("call_id"))}
    todo = [f for f in flagged if f["call_id"] not in done]
    print(f"{len(flagged)} flagged calls, {len(todo)} without a report yet")

    if not todo:
        print("nothing to do")
        return

    calls = (
        db.table("llm_calls")
        .select("id, prompt, response, metadata")
        .in_("id", [t["call_id"] for t in todo])
        .execute()
        .data
    )
    calls_by_id = {c["id"]: c for c in calls}

    for f in todo:
        call = calls_by_id.get(f["call_id"])
        if not call:
            continue
        meta = call["metadata"] or {}
        state = {
            "call_id": call["id"],
            "prompt": call["prompt"],
            "response": call["response"],
            "correct_answers": meta.get("correct_answers") or [],
            "incorrect_answers": meta.get("incorrect_answers") or [],
            "score": f["score"],
        }
        result = graph.invoke(state)

        db.table("incident_reports").insert(
            {
                "call_id": call["id"],
                "verdict": result["verdict"],
                "reasoning": result["reasoning"],
                "report": result["report"],
            }
        ).execute()
        print(f"{result['verdict']:15} {result['report'][:70]}")

    print("done")


if __name__ == "__main__":
    main()
