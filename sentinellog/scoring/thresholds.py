"""Thresholding and calibration diagnostic metrics for unsupervised baselines.

Provides:
1. Unsupervised calibration quantile threshold computation.
2. Calibration diagnostic evaluation (confusion matrix, precision/recall/F1, ROC-AUC, PR-AUC).
3. Calibration error analysis (false positives, false negatives, extreme scores).
4. Clearly separated diagnostic oracle threshold for reference.
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from sentinellog.ingestion.schemas import LogWindow


def compute_unsupervised_threshold(
    calibration_scores: np.ndarray,
    quantile: float = 0.95,
) -> float:
    """Compute unsupervised anomaly decision threshold as a high quantile of calibration scores.

    Args:
        calibration_scores: 1D array of calibration anomaly scores.
        quantile: Quantile in (0, 1), e.g. 0.95.

    Returns:
        Float threshold value.
    """
    if not (0.0 < quantile < 1.0):
        raise ValueError(f"Quantile must be in (0, 1), got {quantile}")
    if len(calibration_scores) == 0:
        raise ValueError("Cannot compute threshold on empty calibration scores.")

    return float(np.quantile(calibration_scores, quantile))


def compute_oracle_threshold(
    calibration_scores: np.ndarray,
    labels: np.ndarray,
    strict: bool = True,
) -> Dict[str, Any]:
    """Find threshold that maximizes F1 score on calibration split (DIAGNOSTIC ORACLE ONLY).

    Labels are used solely for diagnostic reference and must not be used as the primary
    unsupervised baseline threshold.
    """
    if len(calibration_scores) != len(labels):
        raise ValueError("Length mismatch between scores and labels.")

    unique_scores = np.unique(calibration_scores)
    # Subsample candidate thresholds if too many unique scores to maintain fast evaluation
    if len(unique_scores) > 200:
        percentiles = np.linspace(0, 100, 200)
        candidate_thresholds = np.percentile(calibration_scores, percentiles)
    else:
        candidate_thresholds = unique_scores

    best_f1 = -1.0
    best_th = float(candidate_thresholds[0]) if len(candidate_thresholds) > 0 else 0.0
    best_p = 0.0
    best_r = 0.0

    positives = np.sum(labels == 1)
    if positives == 0:
        return {
            "is_oracle": True,
            "diagnostic_only": True,
            "threshold": float(np.max(calibration_scores)) if len(calibration_scores) else 0.0,
            "f1": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "note": "No positive anomaly labels in calibration split.",
        }

    for th in candidate_thresholds:
        preds = (calibration_scores > th) if strict else (calibration_scores >= th)
        tp = np.sum((preds == 1) & (labels == 1))
        fp = np.sum((preds == 1) & (labels == 0))
        fn = np.sum((preds == 0) & (labels == 1))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_th = float(th)
            best_p = float(precision)
            best_r = float(recall)

    return {
        "is_oracle": True,
        "diagnostic_only": True,
        "threshold": best_th,
        "f1": float(best_f1),
        "precision": best_p,
        "recall": best_r,
        "note": "Supervised oracle calibration threshold for theoretical upper bound diagnosis only.",
    }


def _calc_stats(arr: np.ndarray) -> Dict[str, float]:
    """Calculate descriptive statistics for score distributions."""
    if len(arr) == 0:
        return {}
    return {
        "count": int(len(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
    }


def evaluate_calibration_diagnostics(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    windows: Optional[Sequence[LogWindow]] = None,
    quantile: Optional[float] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """Evaluate diagnostic metrics and error cases on the calibration split.

    Args:
        scores: 1D array of anomaly scores.
        labels: 1D array of ground-truth boolean/int anomaly labels.
        threshold: Decision threshold.
        windows: Optional sequence of LogWindow objects for error inspection.
        quantile: Quantile used to derive the unsupervised threshold.
        strict: If True, uses scores > threshold to avoid mass false-positives on discrete score ties.

    Returns:
        Structured dictionary of diagnostic evaluation results.
    """
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=int)

    if len(scores) != len(labels):
        raise ValueError(f"Shape mismatch: {len(scores)} scores vs {len(labels)} labels")

    preds = ((scores > threshold) if strict else (scores >= threshold)).astype(int)

    tp = int(np.sum((preds == 1) & (labels == 1)))
    fp = int(np.sum((preds == 1) & (labels == 0)))
    tn = int(np.sum((preds == 0) & (labels == 0)))
    fn = int(np.sum((preds == 0) & (labels == 1)))

    total = len(labels)
    total_anomalies = int(np.sum(labels == 1))
    total_normals = int(np.sum(labels == 0))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    # ROC-AUC and PR-AUC (require at least one positive and one negative sample)
    roc_auc = None
    pr_auc = None
    if total_anomalies > 0 and total_normals > 0:
        try:
            roc_auc = float(roc_auc_score(labels, scores))
            pr_auc = float(average_precision_score(labels, scores))
        except Exception:
            pass

    # Score distributions
    dist_all = _calc_stats(scores)
    dist_normal = _calc_stats(scores[labels == 0])
    dist_anomalous = _calc_stats(scores[labels == 1])

    # Error analysis: False Positives, False Negatives, Highest scores
    fp_windows: List[Dict[str, Any]] = []
    fn_windows: List[Dict[str, Any]] = []
    highest_windows: List[Dict[str, Any]] = []

    # Rank all by descending score
    ranked_indices = np.argsort(-scores)

    for idx in ranked_indices[:5]:
        item = {
            "index": int(idx),
            "score": float(scores[idx]),
            "label": bool(labels[idx]),
            "predicted": bool(preds[idx]),
        }
        if windows is not None and idx < len(windows):
            w = windows[idx]
            item["window_id"] = w.window_id
            item["record_count"] = w.record_count
            item["template_count"] = len(w.template_ids)
            item["unique_templates"] = sorted(list(set(w.template_ids)))
        highest_windows.append(item)

    # Top FPs
    fp_indices = [idx for idx in ranked_indices if preds[idx] == 1 and labels[idx] == 0]
    for idx in fp_indices[:5]:
        item = {
            "index": int(idx),
            "score": float(scores[idx]),
            "label": False,
            "predicted": True,
        }
        if windows is not None and idx < len(windows):
            w = windows[idx]
            item["window_id"] = w.window_id
            item["record_count"] = w.record_count
            item["unique_templates"] = sorted(list(set(w.template_ids)))
        fp_windows.append(item)

    # Top FNs (lowest score among anomalous windows)
    fn_indices = [idx for idx in np.argsort(scores) if preds[idx] == 0 and labels[idx] == 1]
    for idx in fn_indices[:5]:
        item = {
            "index": int(idx),
            "score": float(scores[idx]),
            "label": True,
            "predicted": False,
        }
        if windows is not None and idx < len(windows):
            w = windows[idx]
            item["window_id"] = w.window_id
            item["record_count"] = w.record_count
            item["unique_templates"] = sorted(list(set(w.template_ids)))
        fn_windows.append(item)

    # Oracle diagnostic comparison
    oracle_res = compute_oracle_threshold(scores, labels, strict=strict)

    return {
        "split": "CALIBRATION_ONLY",
        "threshold_strategy": f"unsupervised_quantile_{quantile}_strict" if quantile else "unsupervised_quantile_strict",
        "threshold": float(threshold),
        "threshold_quantile": float(quantile) if quantile is not None else None,
        "decision_operator": ">" if strict else ">=",
        "total_windows": total,
        "total_anomalies": total_anomalies,
        "total_normals": total_normals,
        "flagged_windows_count": int(tp + fp),
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "metrics": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "specificity": specificity,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
        },
        "score_distribution": {
            "all": dist_all,
            "normal": dist_normal,
            "anomalous": dist_anomalous,
        },
        "error_analysis": {
            "top_false_positives": fp_windows,
            "top_false_negatives": fn_windows,
            "highest_score_windows": highest_windows,
        },
        "oracle_diagnostic": oracle_res,
    }
