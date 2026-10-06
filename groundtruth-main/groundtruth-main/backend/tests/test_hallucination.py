import numpy as np

from app.hallucination import score


def _unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)


def test_response_close_to_correct_is_not_flagged():
    response = _unit([1.0, 0.0])
    correct = np.array([_unit([1.0, 0.05])])      # nearly identical direction
    incorrect = np.array([_unit([0.0, 1.0])])       # orthogonal, far away
    result = score(response, correct, incorrect)
    assert result["score"] > 0
    assert result["flagged"] is False


def test_response_close_to_incorrect_is_flagged():
    response = _unit([0.0, 1.0])
    correct = np.array([_unit([1.0, 0.0])])
    incorrect = np.array([_unit([0.0, 1.0])])        # matches response exactly
    result = score(response, correct, incorrect)
    assert result["score"] < 0
    assert result["flagged"] is True


def test_threshold_is_configurable():
    response = _unit([1.0, 1.0])
    correct = np.array([_unit([1.0, 0.9])])
    incorrect = np.array([_unit([0.9, 1.0])])
    lenient = score(response, correct, incorrect, threshold=-1.0)
    assert lenient["flagged"] is False
