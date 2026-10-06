import numpy as np
import pytest

from app.drift import compute_psi, psi_label


def test_identical_distributions_have_near_zero_psi():
    rng = np.random.default_rng(0)
    data = rng.normal(0, 1, 200)
    assert compute_psi(data, data) < 0.01


def test_clearly_shifted_distribution_is_significant():
    rng = np.random.default_rng(0)
    baseline = rng.normal(0, 1, 200)
    shifted = rng.normal(3, 1, 200)  # far enough to be unmistakable
    assert compute_psi(baseline, shifted) >= 0.25


def test_bins_scale_down_for_small_samples():
    rng = np.random.default_rng(0)
    small = rng.normal(0, 1, 8)
    # Should not raise, and should use the small-sample fallback (<=2 bins)
    value = compute_psi(small, small)
    assert value == pytest.approx(0.0, abs=1e-6)


def test_psi_label_thresholds():
    assert psi_label(0.02) == "none"
    assert psi_label(0.15) == "moderate"
    assert psi_label(0.30) == "significant"
