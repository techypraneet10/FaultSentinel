"""Statistical inference, confidence intervals, and hypothesis tests for Phase 12.

Implements:
- Wilson score interval for binary proportions (avoids flawed normal approximation on extreme rates)
- Deterministic session/window-level bootstrap intervals
- McNemar's paired test for comparing classifiers on identical windows
- Standardized effect size estimators
"""

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import numpy as np


def wilson_score_interval(
    k: Optional[int],
    n: Optional[int],
    confidence: float = 0.95,
) -> Tuple[Optional[float], Optional[float]]:
    """Compute Wilson score interval for a binomial proportion.

    Formula:
        center = (p + z^2 / (2n)) / (1 + z^2 / n)
        half_width = z * sqrt(p(1-p)/n + z^2 / (4n^2)) / (1 + z^2 / n)

    Args:
        k: Number of successes / positives (or None if undefined).
        n: Total number of trials / samples (or None if undefined).
        confidence: Confidence level (default: 0.95 -> z ~ 1.96).

    Returns:
        (lower_bound, upper_bound) clamped to [0.0, 1.0], or (None, None) if undefined.
    """
    if k is None or n is None or n <= 0:
        return (None, None)

    # Standard two-tailed normal quantiles
    z_map = {
        0.90: 1.6448536269514722,
        0.95: 1.959963984540054,
        0.99: 2.5758293035489004,
    }
    z = z_map.get(confidence, 1.959963984540054)

    p = k / n
    denominator = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denominator
    spread = (z * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4.0 * (n**2)))) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    if k == 0:
        lower = 0.0
    if k == n:
        upper = 1.0
    return (float(lower), float(upper))


def bootstrap_ci(
    data: Sequence[Any],
    metric_fn: Callable[[Sequence[Any]], float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Compute deterministic non-parametric bootstrap confidence interval.

    Resampling unit is the window / record index.

    Args:
        data: Sequence of observations.
        metric_fn: Function mapping resampled slice to scalar metric.
        n_resamples: Number of bootstrap replications.
        confidence: Desired coverage probability.
        seed: Fixed random seed for complete determinism.

    Returns:
        (lower_bound, upper_bound).
    """
    if len(data) == 0:
        return (0.0, 0.0)

    rng = np.random.RandomState(seed)
    n = len(data)
    boot_estimates: List[float] = []

    for _ in range(n_resamples):
        indices = rng.choice(n, size=n, replace=True)
        resampled = [data[i] for i in indices]
        try:
            val = metric_fn(resampled)
            if not math.isnan(val):
                boot_estimates.append(val)
        except Exception:
            continue

    if not boot_estimates:
        return (0.0, 0.0)

    alpha = 1.0 - confidence
    lower_pct = 100.0 * (alpha / 2.0)
    upper_pct = 100.0 * (1.0 - alpha / 2.0)

    lower = float(np.percentile(boot_estimates, lower_pct))
    upper = float(np.percentile(boot_estimates, upper_pct))
    return (lower, upper)


def mcnemar_test(
    y_pred_a: Sequence[int],
    y_pred_b: Sequence[int],
    y_true: Optional[Sequence[int]] = None,
    continuity_correction: bool = True,
) -> Dict[str, Any]:
    """Perform McNemar's paired test between two models across paired windows.

    Constructs the exact 2x2 paired contingency table:
        pos_a_pos_b: Model A+, Model B+
        pos_a_neg_b: Model A+, Model B- (b)
        neg_a_pos_b: Model A-, Model B+ (c)
        neg_a_neg_b: Model A-, Model B-

    The discordant cells are:
        b = pos_a_neg_b (Model A positive, Model B negative)
        c = neg_a_pos_b (Model A negative, Model B positive)

    Statistic with Edwards continuity correction:
        chi2 = (|b - c| - 1)^2 / (b + c)
        p-value = erfc(sqrt(chi2 / 2)) from exact chi-square distribution (df=1).

    Args:
        y_pred_a: Binary predictions from Model A (e.g. B0).
        y_pred_b: Binary predictions from Model B (e.g. SentinelLog).
        y_true: Optional ground truth labels to also compute accuracy discordance.
        continuity_correction: Apply Edwards continuity correction (default: True).

    Returns:
        Dict with contingency_table, b, c, statistic, p_value, significant_at_05,
        and optionally accuracy_discordant.
    """
    pa = np.asarray(y_pred_a, dtype=int)
    pb = np.asarray(y_pred_b, dtype=int)

    if len(pa) != len(pb):
        raise ValueError(f"Length mismatch: len(y_pred_a)={len(pa)} != len(y_pred_b)={len(pb)}")

    pos_a_pos_b = int(np.sum((pa == 1) & (pb == 1)))
    pos_a_neg_b = int(np.sum((pa == 1) & (pb == 0)))
    neg_a_pos_b = int(np.sum((pa == 0) & (pb == 1)))
    neg_a_neg_b = int(np.sum((pa == 0) & (pb == 0)))
    total = len(pa)

    b = pos_a_neg_b
    c = neg_a_pos_b
    total_discordant = b + c

    if total_discordant == 0:
        stat = 0.0
        p_value = 1.0
    else:
        diff = abs(b - c)
        if continuity_correction:
            numerator = (max(0.0, diff - 1.0)) ** 2
        else:
            numerator = diff**2
        stat = float(numerator / total_discordant)
        p_value = float(math.erfc(math.sqrt(stat / 2.0)))

    accuracy_discordant = None
    if y_true is not None:
        yt = np.asarray(y_true, dtype=int)
        if len(yt) == len(pa):
            corr_a = (pa == yt)
            corr_b = (pb == yt)
            acc_b = int(np.sum(corr_a & (~corr_b)))
            acc_c = int(np.sum((~corr_a) & corr_b))
            acc_total = acc_b + acc_c
            if acc_total > 0:
                acc_diff = abs(acc_b - acc_c)
                acc_num = (max(0.0, acc_diff - 1.0)) ** 2 if continuity_correction else acc_diff**2
                acc_stat = float(acc_num / acc_total)
                acc_p = float(math.erfc(math.sqrt(acc_stat / 2.0)))
            else:
                acc_stat = 0.0
                acc_p = 1.0
            accuracy_discordant = {
                "b_a_correct_b_incorrect": acc_b,
                "c_a_incorrect_b_correct": acc_c,
                "statistic": acc_stat,
                "p_value": acc_p,
            }

    return {
        "contingency_table": {
            "pos_a_pos_b": pos_a_pos_b,
            "pos_a_neg_b": pos_a_neg_b,
            "neg_a_pos_b": neg_a_pos_b,
            "neg_a_neg_b": neg_a_neg_b,
            "total": total,
        },
        "b": b,
        "c": c,
        "statistic": stat,
        "p_value": p_value,
        "significant_at_05": (p_value < 0.05),
        "accuracy_discordant": accuracy_discordant,
    }


def compute_effect_sizes(
    baseline_metrics: Dict[str, Any],
    proposed_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute absolute and relative effect sizes between baseline and proposed system.

    Handles None values gracefully for undefined metrics.

    Args:
        baseline_metrics: Dict of baseline performance numbers.
        proposed_metrics: Dict of proposed system performance numbers.

    Returns:
        Dict of effect sizes.
    """
    prec_base = baseline_metrics.get("precision")
    prec_prop = proposed_metrics.get("precision")
    delta_prec = float(prec_prop - prec_base) if (prec_prop is not None and prec_base is not None) else None

    rec_base = baseline_metrics.get("recall")
    rec_prop = proposed_metrics.get("recall")
    delta_rec = float(rec_prop - rec_base) if (rec_prop is not None and rec_base is not None) else None

    fpr_base = baseline_metrics.get("fpr")
    fpr_prop = proposed_metrics.get("fpr")
    delta_fpr = float(fpr_prop - fpr_base) if (fpr_prop is not None and fpr_base is not None) else None

    fcr_base = baseline_metrics.get("empirical_false_clear_rate", 0.0)
    fcr_prop = proposed_metrics.get("empirical_false_clear_rate", 0.0)
    delta_fcr = float(fcr_prop - fcr_base) if (fcr_prop is not None and fcr_base is not None) else None

    exp_base = baseline_metrics.get("expensive_calls", 0.0)
    exp_prop = proposed_metrics.get("expensive_calls", 0.0)
    exp_red = float((exp_base - exp_prop) / exp_base) if exp_base > 0 else 0.0

    return {
        "delta_precision": delta_prec,
        "delta_recall": delta_rec,
        "delta_fpr": delta_fpr,
        "delta_false_clear_rate": delta_fcr,
        "expensive_call_reduction_ratio": exp_red,
    }

