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
    k: int,
    n: int,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """Compute Wilson score interval for a binomial proportion.

    Formula:
        center = (p + z^2 / (2n)) / (1 + z^2 / n)
        half_width = z * sqrt(p(1-p)/n + z^2 / (4n^2)) / (1 + z^2 / n)

    Args:
        k: Number of successes / positives.
        n: Total number of trials / samples.
        confidence: Confidence level (default: 0.95 -> z ~ 1.96).

    Returns:
        (lower_bound, upper_bound) clamped to [0.0, 1.0].
    """
    if n <= 0:
        return (0.0, 0.0)

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
    y_true: Sequence[int],
    y_pred_a: Sequence[int],
    y_pred_b: Sequence[int],
    continuity_correction: bool = True,
) -> Dict[str, Any]:
    """Perform McNemar's paired test for differences in binary classification error.

    Constructs 2x2 contingency table:
        b: Model A correct, Model B incorrect
        c: Model A incorrect, Model B correct

    Statistic with Edwards continuity correction:
        chi2 = (|b - c| - 1)^2 / (b + c)
        p-value computed from chi-square distribution with 1 degree of freedom.

    Args:
        y_true: Ground truth labels.
        y_pred_a: Predictions from Model A.
        y_pred_b: Predictions from Model B.
        continuity_correction: Apply Edwards continuity correction.

    Returns:
        Dict with b, c, chi2_statistic, p_value, significant.
    """
    yt = np.asarray(y_true, dtype=int)
    pa = np.asarray(y_pred_a, dtype=int)
    pb = np.asarray(y_pred_b, dtype=int)

    if not (len(yt) == len(pa) == len(pb)):
        raise ValueError("Length mismatch among inputs to McNemar's test.")

    corr_a = (pa == yt)
    corr_b = (pb == yt)

    # b: A correct, B incorrect
    b = int(np.sum(corr_a & (~corr_b)))
    # c: A incorrect, B correct
    c = int(np.sum((~corr_a) & corr_b))

    total_discordant = b + c
    if total_discordant == 0:
        return {
            "b": b,
            "c": c,
            "statistic": 0.0,
            "p_value": 1.0,
            "significant_at_05": False,
        }

    diff = abs(b - c)
    if continuity_correction:
        numerator = (max(0.0, diff - 1.0)) ** 2
    else:
        numerator = diff**2

    stat = float(numerator / total_discordant)

    # p-value via regularized gamma / chi2 cdf approximation
    # For df=1, p = erfc(sqrt(stat / 2))
    p_value = float(math.erfc(math.sqrt(stat / 2.0)))

    return {
        "b": b,
        "c": c,
        "statistic": stat,
        "p_value": p_value,
        "significant_at_05": (p_value < 0.05),
    }


def compute_effect_sizes(
    baseline_metrics: Dict[str, float],
    proposed_metrics: Dict[str, float],
) -> Dict[str, float]:
    """Compute absolute and relative effect sizes between baseline and proposed system.

    Args:
        baseline_metrics: Dict of baseline performance numbers.
        proposed_metrics: Dict of proposed system performance numbers.

    Returns:
        Dict of effect sizes.
    """
    prec_base = baseline_metrics.get("precision", 0.0)
    prec_prop = proposed_metrics.get("precision", 0.0)

    rec_base = baseline_metrics.get("recall", 0.0)
    rec_prop = proposed_metrics.get("recall", 0.0)

    fpr_base = baseline_metrics.get("fpr", 0.0)
    fpr_prop = proposed_metrics.get("fpr", 0.0)

    fcr_base = baseline_metrics.get("empirical_false_clear_rate", 0.0)
    fcr_prop = proposed_metrics.get("empirical_false_clear_rate", 0.0)

    exp_base = baseline_metrics.get("expensive_calls", 0.0)
    exp_prop = proposed_metrics.get("expensive_calls", 0.0)

    return {
        "delta_precision": float(prec_prop - prec_base),
        "delta_recall": float(rec_prop - rec_base),
        "delta_fpr": float(fpr_prop - fpr_base),
        "delta_false_clear_rate": float(fcr_prop - fcr_base),
        "expensive_call_reduction_ratio": float(
            (exp_base - exp_prop) / exp_base if exp_base > 0 else 0.0
        ),
    }
