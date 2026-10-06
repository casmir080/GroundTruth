"""LangGraph pipeline: verify a flagged output against ground truth, then
write a plain-English incident report.

Same shape as Watchtower's classify -> diagnose -> recommend chain:
  verify      -- does the content actually look wrong, not just similarity?
  synthesize  -- turn that judgment into one sentence a non-technical reader gets

The hallucination score (from score_hallucination.py) is the *detector* --
it's already run and decided what's flagged. This pipeline exists to double
check those flags on actual content, which is what catches heuristic false
positives (like a correct "it's safe" answer that just embeds oddly).
"""
from typing import List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .llm import _call_with_retry


class IncidentState(TypedDict):
    call_id: str
    prompt: str
    response: str
    correct_answers: List[str]
    incorrect_answers: List[str]
    score: float
    verdict: Optional[str]
    reasoning: Optional[str]
    report: Optional[str]


def verify_node(state: IncidentState) -> IncidentState:
    correct = "\n".join(f"- {a}" for a in state["correct_answers"][:5]) or "(none given)"
    incorrect = "\n".join(f"- {a}" for a in state["incorrect_answers"][:5]) or "(none given)"

    prompt = f"""You are checking an AI system's answer for factual accuracy.

Question: {state['prompt']}

The AI answered:
{state['response']}

Known correct answers include:
{correct}

Known incorrect (commonly believed but wrong) answers include:
{incorrect}

A similarity-based check flagged this answer as a possible hallucination
(similarity score: {state['score']:.3f}, negative = closer in wording to the
wrong answers). That check only measures wording, not actual correctness.

Judge the AI's answer on what it actually claims, not how it's phrased.
Is the AI's answer factually accurate?
Respond in exactly this format, nothing else:
IS_ACCURATE: yes | no | uncertain
REASONING: <one or two sentences>"""

    resp = _call_with_retry([{"role": "user", "content": prompt}])
    text = resp.choices[0].message.content or ""

    is_accurate, reasoning = None, text.strip()
    for line in text.splitlines():
        if line.upper().startswith("IS_ACCURATE:"):
            is_accurate = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    # Map the model's accuracy judgment to our verdict labels ourselves,
    # rather than asking it to produce "confirmed" / "false_positive"
    # directly -- that phrasing is ambiguous about what's being confirmed,
    # and it silently inverted results in testing.
    if is_accurate == "no":
        verdict = "confirmed"          # the flag was right: this is a hallucination
    elif is_accurate == "yes":
        verdict = "false_positive"     # the flag was wrong: answer is accurate
    else:
        verdict = "uncertain"

    return {**state, "verdict": verdict, "reasoning": reasoning}


def synthesize_node(state: IncidentState) -> IncidentState:
    prompt = f"""Write a one-sentence incident note for a monitoring dashboard.

Question asked: {state['prompt']}
AI's answer (truncated): {state['response'][:200]}
Verdict: {state['verdict']}
Why: {state['reasoning']}

If verdict is 'confirmed', the note must say what the AI incorrectly
claimed -- don't just state the correct fact on its own, since a reader
needs to know what went wrong, not just what's true.
If verdict is 'false_positive', say plainly that the flag was wrong and
the AI's answer was actually accurate.

Write ONE plain-English sentence a non-technical reader would understand.
No preamble, just the sentence."""

    resp = _call_with_retry([{"role": "user", "content": prompt}])
    report = (resp.choices[0].message.content or "").strip()
    return {**state, "report": report}


def build_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("verify", verify_node)
    graph.add_node("synthesize", synthesize_node)
    graph.set_entry_point("verify")
    graph.add_edge("verify", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
