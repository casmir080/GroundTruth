"""PSI (Population Stability Index) drift math, isolated from Supabase/DB
code so it's unit-testable without a network connection.
"""
import numpy as np

SIGNIFICANT = 0.25
MODERATE = 0.10


def compute_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 4) -> float:
    """Higher = more distributional shift between baseline and current.
    Bin count scales down for small samples so a single borderline value
    can't flip the result on its own (see psi_drift.py for why that matters).
    """
    baseline = np.asarray(baseline, dtype=float)
    current = np.asarray(current, dtype=float)
    bins = max(2, min(bins, len(baseline) // 5)) if len(baseline) >= 10 else 2

    edges = np.unique(np.quantile(baseline, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        edges = np.array([-np.inf, np.median(baseline), np.inf])
    else:
        edges[0], edges[-1] = -np.inf, np.inf

    b_counts, _ = np.histogram(baseline, bins=edges)
    c_counts, _ = np.histogram(current, bins=edges)
    b_pct = np.clip(b_counts / len(baseline), 1e-4, None)
    c_pct = np.clip(c_counts / len(current), 1e-4, None)
    return float(np.sum((c_pct - b_pct) * np.log(c_pct / b_pct)))


def psi_label(value: float) -> str:
    if value >= SIGNIFICANT:
        return "significant"
    if value >= MODERATE:
        return "moderate"
    return "none"
