"""Hallucination-flag scoring math, isolated from the embedding model and
Supabase so it's unit-testable with plain vectors.
"""
from typing import TypedDict

import numpy as np

THRESHOLD = 0.0


class HallucinationScore(TypedDict):
    sim_correct: float
    sim_incorrect: float
    score: float
    flagged: bool


def score(
    response_vec: np.ndarray,
    correct_vecs: np.ndarray,
    incorrect_vecs: np.ndarray,
    threshold: float = THRESHOLD,
) -> HallucinationScore:
    """Compare a response embedding against known correct/incorrect answer
    embeddings. Positive score = closer to correct answers; negative =
    closer to incorrect ones (a reminder this is a wording-similarity
    heuristic, not a certified fact-check -- see score_hallucination.py).
    """
    response_vec = np.asarray(response_vec, dtype=float)
    correct_vecs = np.asarray(correct_vecs, dtype=float)
    incorrect_vecs = np.asarray(incorrect_vecs, dtype=float)

    sim_correct = float(np.max(correct_vecs @ response_vec))
    sim_incorrect = float(np.max(incorrect_vecs @ response_vec))
    s = sim_correct - sim_incorrect

    return {
        "sim_correct": sim_correct,
        "sim_incorrect": sim_incorrect,
        "score": s,
        "flagged": s < threshold,
    }
