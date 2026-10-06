"""Classification, selective prediction, and ranking metrics for Phase 12.

Strictly follows research definitions:
- Empirical False Clear Rate = FN / N_total (distinct from conformal miscoverage)
- Escalation Rate = Escalated / N_total
- Auto-Clear Rate = Cleared / N_total
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2PR / (P + R)
- FPR = FP / (FP + TN)
- FNR = FN / (FN + TP)
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence, Union
import numpy as np
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score


@dataclass(frozen=True)
class ClassificationMetrics:
    """Standard binary classification metrics with explicit None for undefined values."""

    tp: int
    tn: int
    fp: int
    fn: int
    total: int
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    fpr: Optional[float]
    fnr: Optional[float]
    accuracy: float
    empirical_false_clear_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelectiveMetrics:
    """Metrics for selective prediction / triage cascade."""

    total_windows: int
    escalated_windows: int
    cleared_windows: int
    escalation_rate: float
    auto_clear_rate: float
    anomalies_escalated: int
    anomalies_cleared: int
    empirical_false_clear_rate: float
    selective_risk: Optional[float]
    precision_escalated: Optional[float]
    recall_escalated: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_classification_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
) -> ClassificationMetrics:
    """Compute binary classification metrics from ground-truth and predictions.

    Handles zero-positive ground truth explicitly:
    - precision is:
        0.0 when predicted positives > 0 and TP == 0
        undefined (None) when predicted positives == 0
    - recall is:
        undefined (None) when actual ground-truth positives (TP + FN) == 0
    - f1 is:
        undefined (None) when actual positives == 0 or precision/recall is None
        0.0 when actual positives > 0, predicted positives > 0, and TP == 0

    Args:
        y_true: Binary ground-truth labels (0 for normal, 1 for anomaly).
        y_pred: Binary predicted labels (0 for normal, 1 for anomaly).

    Returns:
        ClassificationMetrics instance.
    """
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)

    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(y_pred)={len(yp)}")
    if len(yt) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    tp = int(np.sum((yp == 1) & (yt == 1)))
    tn = int(np.sum((yp == 0) & (yt == 0)))
    fp = int(np.sum((yp == 1) & (yt == 0)))
    fn = int(np.sum((yp == 0) & (yt == 1)))
    total = len(yt)

    predicted_positives = tp + fp
    actual_positives = tp + fn
    actual_negatives = fp + tn

    # Precision
    if predicted_positives > 0:
        precision: Optional[float] = float(tp / predicted_positives)
    else:
        precision = None

    # Recall
    if actual_positives > 0:
        recall: Optional[float] = float(tp / actual_positives)
    else:
        recall = None

    # F1
    if (
        actual_positives > 0
        and precision is not None
        and recall is not None
        and (precision + recall) > 0
    ):
        f1: Optional[float] = float(2.0 * precision * recall / (precision + recall))
    elif actual_positives > 0 and predicted_positives > 0 and tp == 0:
        f1 = 0.0
    else:
        f1 = None

    fpr: Optional[float] = float(fp / actual_negatives) if actual_negatives > 0 else None
    fnr: Optional[float] = float(fn / actual_positives) if actual_positives > 0 else None
    accuracy = float((tp + tn) / total) if total > 0 else 0.0
    empirical_false_clear_rate = float(fn / total) if total > 0 else 0.0

    return ClassificationMetrics(
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        total=total,
        precision=precision,
        recall=recall,
        f1=f1,
        fpr=fpr,
        fnr=fnr,
        accuracy=accuracy,
        empirical_false_clear_rate=empirical_false_clear_rate,
    )


def compute_selective_metrics(
    y_true: Sequence[int],
    scores: Sequence[float],
    threshold: float,
    strict: bool = True,
) -> SelectiveMetrics:
    """Compute selective triage metrics given continuous scores and threshold.

    Score > threshold (or >= if strict=False) triggers ESCALATE.

    Args:
        y_true: Binary ground truth labels (0 or 1).
        scores: Continuous anomaly scores.
        threshold: Decision threshold.
        strict: If True, uses score > threshold; if False, score >= threshold.

    Returns:
        SelectiveMetrics instance.
    """
    yt = np.asarray(y_true, dtype=int)
    sc = np.asarray(scores, dtype=np.float64)

    if len(yt) != len(sc):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(scores)={len(sc)}")
    if len(yt) == 0:
        raise ValueError("Cannot compute selective metrics on empty arrays.")

    is_escalated = (sc > threshold) if strict else (sc >= threshold)
    total = len(yt)
    n_escalated = int(np.sum(is_escalated))
    n_cleared = total - n_escalated

    escalation_rate = float(n_escalated / total)
    auto_clear_rate = float(n_cleared / total)

    anomalies_escalated = int(np.sum(is_escalated & (yt == 1)))
    anomalies_cleared = int(np.sum((~is_escalated) & (yt == 1)))

    empirical_false_clear_rate = float(anomalies_cleared / total)
    selective_risk = float(anomalies_cleared / n_cleared) if n_cleared > 0 else None

    precision_escalated = float(anomalies_escalated / n_escalated) if n_escalated > 0 else None
    total_anomalies = int(np.sum(yt == 1))
    recall_escalated = float(anomalies_escalated / total_anomalies) if total_anomalies > 0 else None

    return SelectiveMetrics(
        total_windows=total,
        escalated_windows=n_escalated,
        cleared_windows=n_cleared,
        escalation_rate=escalation_rate,
        auto_clear_rate=auto_clear_rate,
        anomalies_escalated=anomalies_escalated,
        anomalies_cleared=anomalies_cleared,
        empirical_false_clear_rate=empirical_false_clear_rate,
        selective_risk=selective_risk,
        precision_escalated=precision_escalated,
        recall_escalated=recall_escalated,
    )


def compute_pr_auc(y_true: Sequence[int], scores: Sequence[float]) -> Optional[float]:
    """Compute Precision-Recall AUC from continuous scores.

    Returns None if only one class exists in y_true (e.g. zero anomalies).

    Args:
        y_true: Binary ground-truth labels.
        scores: Continuous anomaly scores.

    Returns:
        PR-AUC score [0.0, 1.0] or None if undefined.
    """
    yt = np.asarray(y_true, dtype=int)
    sc = np.asarray(scores, dtype=np.float64)

    if len(np.unique(yt)) < 2:
        return None

    precision, recall, _ = precision_recall_curve(yt, sc)
    return float(auc(recall, precision))


def compute_roc_auc(y_true: Sequence[int], scores: Sequence[float]) -> Optional[float]:
    """Compute ROC-AUC from continuous scores.

    Returns None if only one class exists in y_true (e.g. zero anomalies).

    Args:
        y_true: Binary ground-truth labels.
        scores: Continuous anomaly scores.

    Returns:
        ROC-AUC score [0.0, 1.0] or None if undefined.
    """
    yt = np.asarray(y_true, dtype=int)
    sc = np.asarray(scores, dtype=np.float64)

    if len(np.unique(yt)) < 2:
        return None

    return float(roc_auc_score(yt, sc))

