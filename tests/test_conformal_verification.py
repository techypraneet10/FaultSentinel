"""Comprehensive verification tests for conformal prediction calibration, tie handling, and decision equivalence.

Verifies:
1. All scores unique: strict threshold decision (s > tau) is mathematically identical
   to conformal p-value (p <= alpha) when n >= ceil(1/alpha) - 1.
2. Multiple calibration ties: equivalence holds across tied discrete score clusters.
3. Score exactly equal to threshold (s == tau): evaluates to AUTO-CLEAR under strict
   thresholding and p(s) > alpha under conservative p-value computation.
4. Score just above threshold (tau + eps): evaluates to ESCALATE under both rules (when n >= 1/alpha - 1).
5. Score just below threshold (tau - eps): evaluates to AUTO-CLEAR under both rules.
6. Repeated maximum scores: correct order-statistic capping and tie resolution.
7. Repeated minimum scores: correct lower-tail quantile handling.
8. Small-n / low-alpha boundary condition: when alpha < 1/(n + 1), minimum p-value
   1/(n + 1) > alpha, while capped threshold s_{(n)} escalates points exceeding max(s_i).
9. Exact finite-sample quantile computation across alpha grid (0.01, 0.05, 0.10, 0.20).
10. Monotonicity of threshold with respect to alpha.
11. Extreme edge cases: n = 1 and all identical calibration scores.
12. Risk metric dictionary returns empirical_false_clear_rate with empirical_miscoverage alias.
"""

import math
from typing import List
import numpy as np
import pytest

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import (
    SelectiveGate,
    evaluate_selective_performance,
)


# ---------------------------------------------------------------------------
# 1. All scores unique: Decision equivalence across alphas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("alpha", [0.05, 0.10, 0.20, 0.50])
def test_conformal_unique_scores_decision_equivalence(alpha: float):
    """Verify that when n >= 1/alpha - 1, (s > tau) is mathematically equivalent to (p <= alpha)."""
    n = 20  # For n=20, 1/(n+1) = 1/21 ~ 0.0476 <= alpha for all alpha in [0.05, 0.10, 0.20, 0.50]
    scores = [float(i) for i in range(1, n + 1)]
    calibrator = SplitConformalCalibrator(scores)
    gate = SelectiveGate(calibrator, alpha=alpha, strict=True)
    tau = calibrator.get_threshold(alpha)

    # Test queries spanning below min, calibration values, between calibration values, and above max
    queries = (
        [0.0, 0.5]
        + [float(i) for i in range(1, n + 1)]
        + [i + 0.5 for i in range(1, n)]
        + [float(n) + 0.5, float(n) + 10.0]
    )

    for q in queries:
        threshold_dec = (q > tau)
        gate_dec = (gate.decide(q) == "ESCALATE")
        pval = calibrator.compute_p_value(q)
        pval_dec = (pval <= alpha)

        assert threshold_dec == gate_dec, f"Gate decision mismatch at q={q}"
        assert threshold_dec == pval_dec, (
            f"Decision mismatch at q={q} (tau={tau}, alpha={alpha}, pval={pval:.4f}): "
            f"threshold_dec={threshold_dec}, pval_dec={pval_dec}"
        )


# ---------------------------------------------------------------------------
# 2. Multiple calibration ties: Equivalence under heavy tie clusters
# ---------------------------------------------------------------------------
def test_conformal_multiple_calibration_ties():
    """Verify decision equivalence when calibration scores contain multiple clusters of ties."""
    # 20 scores with duplicate values: [1, 1, 1, 3, 3, 5, 5, 5, 5, 5, 7, 7, 8, 8, 8, 10, 10, 10, 10, 10]
    scores = [1.0, 1.0, 1.0, 3.0, 3.0, 5.0, 5.0, 5.0, 5.0, 5.0,
              7.0, 7.0, 8.0, 8.0, 8.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    n = len(scores)
    calibrator = SplitConformalCalibrator(scores)

    for alpha in [0.05, 0.10, 0.20, 0.50]:
        tau = calibrator.get_threshold(alpha)
        gate = SelectiveGate(calibrator, alpha=alpha, strict=True)

        test_points = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 7.5, 8.0, 9.0, 10.0, 10.5]
        for q in test_points:
            t_dec = (q > tau)
            g_dec = (gate.decide(q) == "ESCALATE")
            pval = calibrator.compute_p_value(q)
            p_dec = (pval <= alpha)

            assert t_dec == g_dec
            assert t_dec == p_dec, (
                f"Tie cluster mismatch at alpha={alpha}, q={q}: "
                f"tau={tau}, t_dec={t_dec}, pval={pval:.4f}, p_dec={p_dec}"
            )


# ---------------------------------------------------------------------------
# 3. Score exactly equal to threshold
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10, 0.20])
def test_conformal_score_exactly_equal_threshold(alpha: float):
    """Verify behavior when query score exactly equals the calibrated threshold."""
    scores = [float(i) for i in range(1, 101)]  # n=100
    calibrator = SplitConformalCalibrator(scores)
    gate = SelectiveGate(calibrator, alpha=alpha, strict=True)
    tau = calibrator.get_threshold(alpha)

    # 1. Strict threshold decision: s > tau is False -> AUTO-CLEAR
    assert gate.decide(tau) == "AUTO-CLEAR"

    # 2. Conformal p-value at s = tau:
    # Under conservative tie handling, count(s_i >= tau) includes s_{(k)} itself and all larger points.
    # Therefore p(tau) = (1 + count(s_i >= tau)) / (n + 1) is strictly > alpha.
    pval = calibrator.compute_p_value(tau)
    assert pval > alpha, f"p(tau)={pval} must be strictly > alpha={alpha}"

    # Both rules agree: AUTO-CLEAR
    assert (tau > tau) == (pval <= alpha) == False


# ---------------------------------------------------------------------------
# 4. Score just above and just below threshold
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("alpha", [0.05, 0.10, 0.20])
def test_conformal_score_just_above_and_below_threshold(alpha: float):
    """Verify behavior in an infinitesimal neighborhood around the threshold."""
    scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
              11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    calibrator = SplitConformalCalibrator(scores)
    gate = SelectiveGate(calibrator, alpha=alpha, strict=True)
    tau = calibrator.get_threshold(alpha)
    eps = 1e-6

    # Score just below: tau - eps
    q_below = tau - eps
    assert gate.decide(q_below) == "AUTO-CLEAR"
    assert calibrator.compute_p_value(q_below) > alpha

    # Score just above: tau + eps
    q_above = tau + eps
    assert gate.decide(q_above) == "ESCALATE"
    assert calibrator.compute_p_value(q_above) <= alpha


# ---------------------------------------------------------------------------
# 5. Repeated maximum scores
# ---------------------------------------------------------------------------
def test_conformal_repeated_maximum_scores():
    """Verify calibration when the maximum score appears repeatedly."""
    scores = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 10.0, 10.0, 10.0, 10.0]  # n=10
    calibrator = SplitConformalCalibrator(scores)

    # For alpha=0.10, k = ceil(11 * 0.9) = 10 -> tau = 10.0
    tau_01 = calibrator.get_threshold(0.10)
    assert tau_01 == 10.0

    # For alpha=0.30, k = ceil(11 * 0.7) = 8 -> tau = 10.0 (tied at max)
    tau_03 = calibrator.get_threshold(0.30)
    assert tau_03 == 10.0

    gate = SelectiveGate(calibrator, alpha=0.10, strict=True)
    # Query at max (10.0): AUTO-CLEAR
    assert gate.decide(10.0) == "AUTO-CLEAR"
    assert calibrator.compute_p_value(10.0) > 0.10

    # Query strictly above max (10.01): ESCALATE
    assert gate.decide(10.01) == "ESCALATE"
    assert calibrator.compute_p_value(10.01) <= 0.10


# ---------------------------------------------------------------------------
# 6. Repeated minimum scores
# ---------------------------------------------------------------------------
def test_conformal_repeated_minimum_scores():
    """Verify calibration when minimum score appears repeatedly."""
    scores = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]  # n=10
    calibrator = SplitConformalCalibrator(scores)

    # For alpha=0.80, k = ceil(11 * 0.2) = 3 -> tau = 0.0
    tau_08 = calibrator.get_threshold(0.80)
    assert tau_08 == 0.0

    gate = SelectiveGate(calibrator, alpha=0.80, strict=True)
    assert gate.decide(0.0) == "AUTO-CLEAR"
    assert gate.decide(0.001) == "ESCALATE"


# ---------------------------------------------------------------------------
# 7. All identical calibration scores
# ---------------------------------------------------------------------------
def test_conformal_all_identical_calibration_scores():
    """Verify behavior when all calibration nonconformity scores are identical."""
    scores = [5.0] * 20  # n=20
    calibrator = SplitConformalCalibrator(scores)
    tau = calibrator.get_threshold(0.05)
    assert tau == 5.0

    gate = SelectiveGate(calibrator, alpha=0.05, strict=True)
    # Any query <= 5.0 is AUTO-CLEAR
    assert gate.decide(4.9) == "AUTO-CLEAR"
    assert gate.decide(5.0) == "AUTO-CLEAR"

    # Any query > 5.0 is strictly greater than all calibration points -> ESCALATE
    assert gate.decide(5.01) == "ESCALATE"
    assert calibrator.compute_p_value(5.01) <= 0.05


# ---------------------------------------------------------------------------
# 8. Boundary condition: alpha < 1 / (n + 1)
# ---------------------------------------------------------------------------
def test_conformal_small_sample_boundary_discrepancy():
    """Document and verify behavior when sample size n is too small for alpha (alpha < 1/(n+1)).

    In this regime:
    - Minimum p-value is 1 / (n + 1) > alpha, so (p <= alpha) is NEVER True (0% escalation).
    - Capped threshold k_capped = n gives tau = max(s_i), so (s > tau) escalates points
      strictly exceeding the calibration maximum.
    - SentinelLog designates (s > tau) as the primary operational decision rule.
    """
    n = 3
    alpha = 0.10
    # Here 1 / (n + 1) = 0.25 > alpha = 0.10
    scores = [1.0, 2.0, 3.0]
    calibrator = SplitConformalCalibrator(scores)
    tau = calibrator.get_threshold(alpha)
    assert tau == 3.0  # capped at s_{(3)}

    gate = SelectiveGate(calibrator, alpha=alpha, strict=True)

    # For query s = 3.5 > max(s_i):
    q = 3.5
    gate_decision = gate.decide(q)
    threshold_decision = (q > tau)
    pval = calibrator.compute_p_value(q)
    pval_decision = (pval <= alpha)

    # Gate follows the primary threshold rule:
    assert gate_decision == "ESCALATE"
    assert threshold_decision is True

    # P-value rule cannot escalate because 1/(3+1) = 0.25 > 0.10:
    assert pval == 0.25
    assert pval_decision is False

    # Document that this is a recognized finite-sample boundary distinction:
    assert threshold_decision != pval_decision


# ---------------------------------------------------------------------------
# 9. n = 1 edge case
# ---------------------------------------------------------------------------
def test_conformal_n_equals_one():
    """Verify calibration with single calibration sample (n = 1)."""
    calibrator = SplitConformalCalibrator([4.2])
    tau = calibrator.get_threshold(0.05)
    assert tau == 4.2

    gate = SelectiveGate(calibrator, alpha=0.05, strict=True)
    assert gate.decide(4.2) == "AUTO-CLEAR"
    assert gate.decide(4.2001) == "ESCALATE"
    # p-value for n=1 is at least 1/2 = 0.50
    assert calibrator.compute_p_value(4.2001) == 0.50


# ---------------------------------------------------------------------------
# 10. Monotonicity across alpha grid (0.01, 0.05, 0.10, 0.20)
# ---------------------------------------------------------------------------
def test_conformal_alpha_grid_and_monotonicity():
    """Verify that calibrated threshold is monotonically non-increasing in alpha."""
    np.random.seed(42)
    scores = np.random.exponential(scale=1.0, size=200).tolist()
    calibrator = SplitConformalCalibrator(scores)

    alphas = [0.01, 0.05, 0.10, 0.20, 0.50]
    thresholds = [calibrator.get_threshold(a) for a in alphas]

    for i in range(len(thresholds) - 1):
        assert thresholds[i] >= thresholds[i + 1], (
            f"Monotonicity violation: tau({alphas[i]})={thresholds[i]} < tau({alphas[i+1]})={thresholds[i+1]}"
        )


# ---------------------------------------------------------------------------
# 11. Metric dictionary naming and backward compatibility
# ---------------------------------------------------------------------------
def test_selective_performance_metric_naming():
    """Verify that evaluate_selective_performance returns empirical_false_clear_rate and alias."""
    scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    labels = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]  # 2 anomalies at 9.0 and 10.0
    calibrator = SplitConformalCalibrator(scores)

    perf = evaluate_selective_performance(scores, labels, calibrator, alpha=0.20, strict=True)

    # Both precise name and backward compatibility alias must be present with identical values
    assert "empirical_false_clear_rate" in perf
    assert "empirical_miscoverage" in perf
    assert perf["empirical_false_clear_rate"] == perf["empirical_miscoverage"]

    # False clears: anomaly at 9.0 was auto-cleared (score 9.0 <= tau 9.0) -> FN = 1
    # Total windows = 10 -> empirical_false_clear_rate = 1 / 10 = 0.10
    assert perf["false_clears_count"] == 1
    assert perf["empirical_false_clear_rate"] == 0.10
    assert perf["deviation_from_nominal"] == pytest.approx(0.10 - 0.20)
