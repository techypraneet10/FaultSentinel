"""B0: Simple template-frequency and rarity baseline anomaly detector.

Implements a transparent classical baseline that estimates template frequency
distributions strictly from training windows, assigning an unsupervised window-level
rarity score (mean negative log-frequency). Higher scores indicate higher anomaly likelihood.
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from sentinellog.ingestion.schemas import LogWindow, UNKNOWN_TEMPLATE_ID


class FrequencyScorer:
    """Unsupervised frequency baseline (B0) based on template rarity.

    Mathematical Formulation:
        Let V_train be the set of distinct templates observed in TRAIN, plus UNKNOWN (-1).
        Let C_train(t) be the total token count of template t in TRAIN.
        Let N_train = sum_t C_train(t) be total tokens in TRAIN.
        With additive smoothing parameter alpha > 0:
            P_train(t) = (C_train(t) + alpha) / (N_train + alpha * (|V_train| + 1))

        For a window W = (t_1, t_2, ..., t_L) with L = record_count:
            rarity(t_i) = -log P_train(t_i)
            Score_B0(W) = (1 / L) * sum_{i=1}^L rarity(t_i)

        Higher score = higher average rarity (surprise) = more anomalous.
    """

    def __init__(self, alpha: float = 1.0):
        """Initialize FrequencyScorer.

        Args:
            alpha: Laplace smoothing parameter (alpha > 0).
        """
        if alpha <= 0:
            raise ValueError(f"Smoothing parameter alpha must be > 0, got {alpha}")
        self.alpha = float(alpha)
        self.is_fitted = False

        self.vocabulary_: Dict[int, int] = {}  # template_id -> token_count in train
        self.total_tokens_: int = 0
        self.log_probabilities_: Dict[int, float] = {}  # template_id -> log P(t)
        self.unknown_log_prob_: float = 0.0

    def fit(self, windows: Sequence[LogWindow]) -> "FrequencyScorer":
        """Fit template frequency distribution exclusively on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        counts: Dict[int, int] = {}
        total = 0

        for w in windows:
            for tid in w.template_ids:
                counts[tid] = counts.get(tid, 0) + 1
                total += 1

        self.total_tokens_ = total
        self.vocabulary_ = dict(counts)

        # Number of unique categories including UNKNOWN (-1)
        unique_templates = set(counts.keys())
        unique_templates.add(UNKNOWN_TEMPLATE_ID)
        v_size = len(unique_templates)

        denominator = float(total) + self.alpha * float(v_size)

        # Compute log probabilities with smoothing
        self.log_probabilities_ = {}
        for tid, cnt in counts.items():
            prob = (float(cnt) + self.alpha) / denominator
            self.log_probabilities_[tid] = float(np.log(prob))

        # Log prob for UNKNOWN or unseen template
        unknown_cnt = counts.get(UNKNOWN_TEMPLATE_ID, 0)
        unknown_prob = (float(unknown_cnt) + self.alpha) / denominator
        self.unknown_log_prob_ = float(np.log(unknown_prob))
        self.log_probabilities_[UNKNOWN_TEMPLATE_ID] = self.unknown_log_prob_

        self.is_fitted = True
        return self

    def score_window(self, window: LogWindow) -> float:
        """Compute B0 rarity score for a single window.

        Args:
            window: LogWindow instance.

        Returns:
            Float anomaly score (higher = more anomalous).
        """
        if not self.is_fitted:
            raise RuntimeError("FrequencyScorer must be fitted before scoring.")

        if not window.template_ids:
            return 0.0

        total_surprisal = 0.0
        for tid in window.template_ids:
            log_p = self.log_probabilities_.get(tid, self.unknown_log_prob_)
            total_surprisal += -log_p

        return float(total_surprisal / len(window.template_ids))

    def score(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Compute B0 rarity scores for a sequence of windows.

        Args:
            windows: Sequence of LogWindow instances.

        Returns:
            1D numpy array of float anomaly scores (higher = more anomalous).
        """
        return np.array([self.score_window(w) for w in windows], dtype=np.float64)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable metadata describing fitted baseline."""
        if not self.is_fitted:
            raise RuntimeError("Scorer not fitted.")

        return {
            "baseline": "B0",
            "name": "FrequencyScorer",
            "alpha": self.alpha,
            "total_tokens_train": self.total_tokens_,
            "vocabulary_size": len(self.log_probabilities_),
            "known_templates_count": len([k for k in self.log_probabilities_ if k != UNKNOWN_TEMPLATE_ID]),
            "unknown_log_probability": self.unknown_log_prob_,
            "score_direction": "higher_is_more_anomalous",
        }
