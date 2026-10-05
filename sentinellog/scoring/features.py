"""Feature extraction and template vectorization for baseline anomaly detection.

Provides deterministic template count vectorization derived strictly from
training vocabulary, ensuring vocabulary stability and zero leakage into
feature dimensions.
"""

from typing import Any, Dict, List, Literal, Optional, Sequence, Set
import numpy as np

from sentinellog.ingestion.schemas import LogWindow, UNKNOWN_TEMPLATE_ID


NormalizationMode = Literal["normalized_count", "log1p_count", "raw_count"]


class TemplateCountVectorizer:
    """Extracts fixed-dimensional count vectors from log windows.

    The vocabulary is fitted strictly on training windows and frozen. Novel or
    unknown templates encountered during calibration or inference map exclusively
    to the UNKNOWN (-1) bin, preserving invariant dimensionality.
    """

    def __init__(
        self,
        mode: NormalizationMode = "normalized_count",
    ):
        """Initialize vectorizer.

        Args:
            mode: Normalization strategy:
                - 'normalized_count': count / total_records_in_window (robust to variable lengths)
                - 'log1p_count': log(1 + count)
                - 'raw_count': unnormalized integer counts
        """
        self.mode = mode
        self.is_fitted = False
        self.vocabulary_: Dict[int, int] = {}  # template_id -> feature_index
        self.inverse_vocabulary_: List[int] = []  # feature_index -> template_id
        self.feature_names_: List[str] = []
        self.unknown_idx_: int = -1

    def fit(self, windows: Sequence[LogWindow]) -> "TemplateCountVectorizer":
        """Fit vocabulary exclusively on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        seen_templates: Set[int] = set()
        for w in windows:
            seen_templates.update(w.template_ids)

        # Remove UNKNOWN_TEMPLATE_ID if present, it will be added explicitly
        seen_templates.discard(UNKNOWN_TEMPLATE_ID)

        # Sort known templates for deterministic ordering
        sorted_known = sorted(seen_templates)

        self.vocabulary_ = {}
        self.inverse_vocabulary_ = []
        self.feature_names_ = []

        for idx, tid in enumerate(sorted_known):
            self.vocabulary_[tid] = idx
            self.inverse_vocabulary_.append(tid)
            self.feature_names_.append(f"template_{tid}")

        # Explicit bin for UNKNOWN template (-1)
        self.unknown_idx_ = len(self.inverse_vocabulary_)
        self.vocabulary_[UNKNOWN_TEMPLATE_ID] = self.unknown_idx_
        self.inverse_vocabulary_.append(UNKNOWN_TEMPLATE_ID)
        self.feature_names_.append("template_UNKNOWN")

        self.is_fitted = True
        return self

    def transform(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Transform windows into a 2D numpy feature matrix.

        Args:
            windows: Sequence of LogWindow instances.

        Returns:
            2D numpy array of shape (len(windows), len(vocabulary_))
        """
        if not self.is_fitted:
            raise RuntimeError("TemplateCountVectorizer must be fitted before transform.")

        n_samples = len(windows)
        n_features = len(self.inverse_vocabulary_)
        matrix = np.zeros((n_samples, n_features), dtype=np.float64)

        for i, w in enumerate(windows):
            for tid in w.template_ids:
                feature_idx = self.vocabulary_.get(tid, self.unknown_idx_)
                matrix[i, feature_idx] += 1.0

            total_records = float(w.record_count) if w.record_count > 0 else 1.0

            if self.mode == "normalized_count":
                matrix[i, :] /= total_records
            elif self.mode == "log1p_count":
                matrix[i, :] = np.log1p(matrix[i, :])
            elif self.mode == "raw_count":
                pass
            else:
                raise ValueError(f"Unknown normalization mode: {self.mode}")

        return matrix

    def fit_transform(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Fit vocabulary and transform windows in one step."""
        return self.fit(windows).transform(windows)

    @property
    def n_features(self) -> int:
        """Number of feature dimensions."""
        if not self.is_fitted:
            raise RuntimeError("Vectorizer not fitted.")
        return len(self.inverse_vocabulary_)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable metadata describing vocabulary and configuration."""
        return {
            "mode": self.mode,
            "n_features": self.n_features if self.is_fitted else 0,
            "vocabulary": {str(k): v for k, v in self.vocabulary_.items()},
            "feature_names": self.feature_names_,
            "unknown_idx": self.unknown_idx_,
        }
