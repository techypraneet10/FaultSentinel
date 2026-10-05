"""Split conformal prediction calibration engine.

Provides finite-sample inductive conformal calibration over calibration nonconformity scores:
- Exact order-statistic quantile computation: ceil((n + 1) * (1 - alpha)) / n
- Conformal p-value computation with explicit conservative tie handling
- Full calibration metadata and finite-sample audit traceability

IMPORTANT STATISTICAL FRAMING & CONFORMAL GUARANTEE INTERPRETATION:
1. Conformal Score-Tail / Escalation Control:
   The unsupervised split conformal procedure calibrates an anomaly score threshold tau_alpha
   over calibration nonconformity scores s_1, ..., s_n. Under the relevant exchangeability
   assumption, the upper-tail probability of the nonconformity score is bounded:
       P(S_{test} > tau_alpha) <= alpha  (or P(S_{test} <= tau_alpha) >= 1 - alpha)
   This bounds the probability that a random test point from the calibration distribution is escalated.

2. Anomaly False-Negative / Incident Risk Control:
   Anomaly labels are NOT used in the conformal calibration procedure.
   Therefore, this procedure does NOT guarantee:
       P(ANOMALY AND AUTO-CLEAR) <= alpha
   nor does it guarantee false-negative rate <= alpha, missed-incident rate <= alpha, or FDR <= alpha.
   The anomaly false-clear rate is an EMPIRICAL DIAGNOSTIC, not a conformal guarantee.

3. Under temporal log data with potential non-stationarity, finite-sample guarantees
   serve as an empirical calibration framework rather than distribution-free exchangeability
   guarantees.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np


class SplitConformalCalibrator:
    """Inductive split conformal calibrator for nonconformity scores.

    Nonconformity Score Orientation:
        Higher score = more anomalous.

    Conformal Threshold:
        For calibration scores s_1, ..., s_n and significance level alpha in (0, 1):
            k = ceil((n + 1) * (1 - alpha))
            k_capped = min(n, max(1, k))
            threshold_alpha = s_{(k_capped)}   (1-indexed sorted ascending)

    Conformal p-value:
        p(s) = (1 + sum_{i=1}^n I(s_i >= s)) / (n + 1)
        Small p-value <= alpha indicates significant deviation from calibration normal mass.

    Threshold vs. P-Value Equivalence & Decision Rule:
        - When n >= ceil(1 / alpha) - 1 (i.e., alpha >= 1 / (n + 1)):
          The strict threshold decision (s > tau_alpha) is provably mathematically identical
          to (p(s) <= alpha) for all query scores s in R, including tied calibration values.
        - When n < 1 / alpha - 1 (i.e., alpha < 1 / (n + 1)):
          The minimum possible p-value is 1 / (n + 1) > alpha, so p(s) <= alpha is NEVER satisfied.
          However, the capped order-statistic threshold k_capped = n yields tau_alpha = s_{(n)},
          escalating points with s > max(s_i).
        The primary operational decision rule throughout SentinelLog is the threshold rule
        (score > tau_alpha).
    """

    def __init__(self, calibration_scores: Optional[Sequence[float]] = None):
        """Initialize calibrator.

        Args:
            calibration_scores: Optional 1D array of calibration scores.
        """
        self.scores_: np.ndarray = np.array([], dtype=np.float64)
        self.n_calib_: int = 0
        self.is_calibrated: bool = False

        if calibration_scores is not None:
            self.fit(calibration_scores)

    def fit(self, calibration_scores: Sequence[float]) -> "SplitConformalCalibrator":
        """Calibrate using calibration nonconformity scores.

        Args:
            calibration_scores: Sequence of calibration nonconformity scores.

        Returns:
            self
        """
        arr = np.asarray(calibration_scores, dtype=np.float64)
        if len(arr) == 0:
            raise ValueError("Cannot calibrate on empty scores array.")

        self.scores_ = np.sort(arr)
        self.n_calib_ = len(self.scores_)
        self.is_calibrated = True
        return self

    def get_threshold(self, alpha: float) -> float:
        """Compute finite-sample conformal threshold for significance level alpha.

        Args:
            alpha: Significance level in (0, 1). Target coverage is 1 - alpha.

        Returns:
            Float threshold value.
        """
        if not self.is_calibrated:
            raise RuntimeError("SplitConformalCalibrator must be fitted before obtaining threshold.")
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"Significance level alpha must be in (0, 1), got {alpha}")

        n = self.n_calib_
        # 1-indexed order statistic index
        rank = math.ceil((n + 1) * (1.0 - alpha))
        rank_capped = min(n, max(1, rank))

        # Convert to 0-indexed index
        threshold_val = float(self.scores_[rank_capped - 1])
        return threshold_val

    def compute_p_value(self, score: float) -> float:
        """Compute conformal p-value for a query score.

        Formula:
            p(s) = (1 + sum_{i=1}^n I(s_i >= s)) / (n + 1)
        """
        if not self.is_calibrated:
            raise RuntimeError("Calibrator must be fitted before computing p-values.")

        n = self.n_calib_
        # Count calibration scores >= score (conservative tie handling)
        greater_equal_count = int(np.sum(self.scores_ >= score))
        p_val = (1.0 + float(greater_equal_count)) / float(n + 1)
        return float(p_val)

    def compute_p_values(self, scores: Sequence[float]) -> np.ndarray:
        """Vectorized conformal p-value computation."""
        return np.array([self.compute_p_value(s) for s in scores], dtype=np.float64)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable calibration metadata."""
        if not self.is_calibrated:
            raise RuntimeError("Calibrator not fitted.")

        return {
            "n_calibration": self.n_calib_,
            "min_score": float(self.scores_[0]),
            "max_score": float(self.scores_[-1]),
            "mean_score": float(np.mean(self.scores_)),
            "median_score": float(np.median(self.scores_)),
            "score_direction": "higher_is_more_anomalous",
            "conformal_convention": "finite_sample_ceil_n_plus_one",
        }
