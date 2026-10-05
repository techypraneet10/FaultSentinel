"""Selective escalation gate and risk-coverage evaluation engine.

Implements the selective prediction decision:
    Score > Threshold (or Conformal p-value <= alpha) -> ESCALATE
    Score <= Threshold (or Conformal p-value > alpha) -> AUTO-CLEAR

Evaluates coverage, selective risk, empirical miscoverage, and deviation from nominal alpha.
"""

from typing import Any, Dict, List, Literal, Optional, Sequence, Union
import numpy as np

from sentinellog.calibration.conformal import SplitConformalCalibrator


Decision = Literal["AUTO-CLEAR", "ESCALATE"]


class SelectiveGate:
    """Selective prediction escalation gate using calibrated conformal thresholds."""

    def __init__(
        self,
        calibrator: SplitConformalCalibrator,
        alpha: float = 0.05,
        strict: bool = True,
    ):
        """Initialize gate.

        Args:
            calibrator: Fitted SplitConformalCalibrator instance.
            alpha: Nominal significance level.
            strict: If True, uses score > threshold to handle tied discrete values.
        """
        self.calibrator = calibrator
        self.alpha = float(alpha)
        self.strict = strict
        self.threshold = calibrator.get_threshold(alpha)

    def decide(self, score: float) -> Decision:
        """Make triage decision for a single window score."""
        is_escalated = (score > self.threshold) if self.strict else (score >= self.threshold)
        return "ESCALATE" if is_escalated else "AUTO-CLEAR"

    def decide_batch(self, scores: Sequence[float]) -> List[Decision]:
        """Make triage decisions for a sequence of window scores."""
        return [self.decide(s) for s in scores]


def evaluate_selective_performance(
    scores: Sequence[float],
    labels: Sequence[int],
    calibrator: SplitConformalCalibrator,
    alpha: float = 0.05,
    strict: bool = True,
) -> Dict[str, Any]:
    """Compute detailed selective prediction and risk-coverage metrics.

    Definitions:
        - Escalation Rate = Escalated / Total
        - Coverage (Auto-Clear Rate) = Auto-Cleared / Total
        - False Clear = Ground-truth anomalous window auto-cleared (FN)
        - Selective Risk = False Clears / Total Auto-Cleared
        - Empirical Miscoverage = False Clears / Total Windows
        - Deviation = Empirical Miscoverage - Nominal Alpha
    """
    scores_arr = np.asarray(scores, dtype=np.float64)
    labels_arr = np.asarray(labels, dtype=int)
    n_total = len(scores_arr)

    if n_total != len(labels_arr):
        raise ValueError("Length mismatch between scores and labels.")

    gate = SelectiveGate(calibrator=calibrator, alpha=alpha, strict=strict)
    decisions = gate.decide_batch(scores_arr)

    preds_escalated = np.array([1 if d == "ESCALATE" else 0 for d in decisions], dtype=int)

    tp = int(np.sum((preds_escalated == 1) & (labels_arr == 1)))
    fp = int(np.sum((preds_escalated == 1) & (labels_arr == 0)))
    tn = int(np.sum((preds_escalated == 0) & (labels_arr == 0)))
    fn = int(np.sum((preds_escalated == 0) & (labels_arr == 1)))  # False clears

    n_escalated = tp + fp
    n_cleared = tn + fn

    escalation_rate = float(n_escalated / n_total) if n_total > 0 else 0.0
    coverage = float(n_cleared / n_total) if n_total > 0 else 0.0

    precision = float(tp / n_escalated) if n_escalated > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Risk metrics
    selective_risk = float(fn / n_cleared) if n_cleared > 0 else 0.0
    empirical_miscoverage = float(fn / n_total) if n_total > 0 else 0.0
    deviation = float(empirical_miscoverage - alpha)

    return {
        "nominal_alpha": float(alpha),
        "conformal_threshold": float(gate.threshold),
        "total_windows": n_total,
        "total_anomalies": int(np.sum(labels_arr == 1)),
        "n_escalated": n_escalated,
        "n_cleared": n_cleared,
        "escalation_rate": escalation_rate,
        "coverage": coverage,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "escalation_precision": precision,
        "escalation_recall": recall,
        "escalation_f1": f1,
        "false_clears_count": fn,
        "selective_risk": selective_risk,
        "empirical_miscoverage": empirical_miscoverage,
        "deviation_from_nominal": deviation,
    }


def sweep_alpha_grid(
    scores: Sequence[float],
    labels: Sequence[int],
    calibrator: SplitConformalCalibrator,
    alpha_grid: Sequence[float] = (0.01, 0.05, 0.10, 0.20),
    strict: bool = True,
) -> List[Dict[str, Any]]:
    """Evaluate selective gate across predefined target alpha grid."""
    results: List[Dict[str, Any]] = []
    for alpha in alpha_grid:
        res = evaluate_selective_performance(
            scores=scores,
            labels=labels,
            calibrator=calibrator,
            alpha=alpha,
            strict=strict,
        )
        results.append(res)
    return results
