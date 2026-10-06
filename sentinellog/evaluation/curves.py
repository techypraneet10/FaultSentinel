"""Curve generation for Precision-at-Coverage and Risk-Coverage in Phase 12.

Strictly adheres to research constraints:
- Operating points derived from frozen thresholds or calibration percentiles (no test tuning)
- Explicit mathematical definitions of coverage and risk:
    - Escalation Coverage = Escalated Windows / Total Windows
    - Auto-Clear Coverage = Auto-Cleared Windows / Total Windows
    - Selective Risk = Auto-Cleared Anomalies / Total Auto-Cleared (False Clears / Cleared)
    - Empirical False-Clear Rate = Auto-Cleared Anomalies / Total Windows (FN / N_total)
"""

from typing import Any, Dict, List, Sequence
import numpy as np

from sentinellog.evaluation.metrics import compute_selective_metrics


def generate_precision_at_coverage(
    y_true: Sequence[int],
    scores: Sequence[float],
    thresholds: Sequence[float],
    operating_point_names: Sequence[str],
    strict: bool = True,
) -> List[Dict[str, Any]]:
    """Compute precision, recall, FPR, and empirical false-clear rate across operating points.

    Args:
        y_true: Ground truth binary labels.
        scores: Continuous anomaly scores.
        thresholds: Predetermined sequence of frozen thresholds.
        operating_point_names: Labels identifying each point (e.g. 'alpha=0.01', 'alpha=0.05').
        strict: Threshold inequality mode.

    Returns:
        List of dicts containing operating point telemetry.
    """
    points = []
    for name, th in zip(operating_point_names, thresholds):
        sel = compute_selective_metrics(y_true, scores, threshold=th, strict=strict)

        yt = np.asarray(y_true, dtype=int)
        sc = np.asarray(scores, dtype=np.float64)
        is_esc = (sc > th) if strict else (sc >= th)

        tp = int(np.sum(is_esc & (yt == 1)))
        fp = int(np.sum(is_esc & (yt == 0)))
        tn = int(np.sum((~is_esc) & (yt == 0)))
        fn = int(np.sum((~is_esc) & (yt == 1)))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        points.append({
            "operating_point": name,
            "threshold": float(th),
            "escalation_coverage": sel.escalation_rate,
            "auto_clear_coverage": sel.auto_clear_rate,
            "precision": precision,
            "recall": recall,
            "fpr": fpr,
            "selective_risk": sel.selective_risk,
            "empirical_false_clear_rate": sel.empirical_false_clear_rate,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        })

    return points


def generate_risk_coverage_curve(
    y_true: Sequence[int],
    scores: Sequence[float],
    threshold_grid: Sequence[float],
    strict: bool = True,
) -> List[Dict[str, float]]:
    """Generate risk versus coverage curve points across a grid of thresholds.

    Args:
        y_true: Ground-truth binary labels.
        scores: Continuous scores.
        threshold_grid: Pre-sorted threshold operating values.
        strict: Threshold inequality mode.

    Returns:
        List of dicts containing threshold, coverage, risk, and false-clear rate.
    """
    curve = []
    for th in threshold_grid:
        sel = compute_selective_metrics(y_true, scores, threshold=th, strict=strict)
        curve.append({
            "threshold": float(th),
            "escalation_rate": sel.escalation_rate,
            "auto_clear_coverage": sel.auto_clear_rate,
            "selective_risk": sel.selective_risk,
            "empirical_false_clear_rate": sel.empirical_false_clear_rate,
        })
    return curve
