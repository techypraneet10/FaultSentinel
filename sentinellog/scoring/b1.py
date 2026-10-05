"""B1: Template-count vector anomaly detection baselines.

Implements classical multivariate unsupervised anomaly detectors over template count
vectors derived from the frozen training vocabulary:
1. PCAScorer (Primary B1): Reconstruction error from principal component projection.
2. IsolationForestScorer (Secondary B1): Ensemble isolation tree depth anomaly scoring.
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.scoring.features import NormalizationMode, TemplateCountVectorizer


class PCAScorer:
    """B1 Primary: PCA Reconstruction Error Anomaly Detector.

    Mathematical Formulation:
        1. Template count vectors x in R^D are constructed using the frozen training vocabulary.
        2. PCA is fitted strictly on TRAIN vectors:
               x_centered = x - mu
               z = x_centered * W_k  (projection to k principal components)
               x_hat = z * W_k^T + mu  (reconstruction)
        3. Anomaly score:
               Score_PCA(x) = ||x - x_hat||_2^2 = sum_{j=1}^D (x_j - x_hat_j)^2
        Higher reconstruction error indicates deviation from the normal subspace (more anomalous).
    """

    def __init__(
        self,
        mode: NormalizationMode = "normalized_count",
        variance_ratio: Optional[float] = 0.95,
        n_components: Optional[int] = None,
        random_state: int = 42,
    ):
        """Initialize PCAScorer.

        Args:
            mode: Feature normalization mode ('normalized_count', 'log1p_count', 'raw_count').
            variance_ratio: Target cumulative explained variance ratio to select k components.
            n_components: Exact number of components (overrides variance_ratio if provided).
            random_state: Deterministic seed for PCA solver.
        """
        self.mode = mode
        self.variance_ratio = variance_ratio
        self.n_components_cfg = n_components
        self.random_state = random_state

        self.vectorizer = TemplateCountVectorizer(mode=mode)
        self.pca: Optional[PCA] = None
        self.is_fitted = False

        self.k_components_: int = 0
        self.explained_variance_ratio_: List[float] = []
        self.cumulative_variance_: float = 0.0

    def fit(self, windows: Sequence[LogWindow]) -> "PCAScorer":
        """Fit vectorizer and PCA strictly on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        X_train = self.vectorizer.fit_transform(windows)
        n_samples, n_features = X_train.shape

        max_possible_k = min(n_samples, n_features)

        if self.n_components_cfg is not None:
            k = min(int(self.n_components_cfg), max_possible_k)
            self.pca = PCA(n_components=k, random_state=self.random_state)
            self.pca.fit(X_train)
        elif self.variance_ratio is not None:
            # Fit full PCA to determine required components for variance target
            full_pca = PCA(n_components=max_possible_k, random_state=self.random_state)
            full_pca.fit(X_train)

            cum_var = np.cumsum(full_pca.explained_variance_ratio_)
            k = int(np.searchsorted(cum_var, self.variance_ratio) + 1)
            k = max(1, min(k, max_possible_k))

            self.pca = PCA(n_components=k, random_state=self.random_state)
            self.pca.fit(X_train)
        else:
            k = min(5, max_possible_k)
            self.pca = PCA(n_components=k, random_state=self.random_state)
            self.pca.fit(X_train)

        self.k_components_ = int(self.pca.n_components_)
        self.explained_variance_ratio_ = [float(v) for v in self.pca.explained_variance_ratio_]
        self.cumulative_variance_ = float(np.sum(self.pca.explained_variance_ratio_))

        self.is_fitted = True
        return self

    def score(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Compute PCA reconstruction error for given windows.

        Args:
            windows: Sequence of LogWindow instances.

        Returns:
            1D numpy array of reconstruction errors (higher = more anomalous).
        """
        if not self.is_fitted or self.pca is None:
            raise RuntimeError("PCAScorer must be fitted before scoring.")

        X = self.vectorizer.transform(windows)
        X_projected = self.pca.transform(X)
        X_reconstructed = self.pca.inverse_transform(X_projected)

        # Squared reconstruction error per window: sum((x - x_hat)^2)
        diff = X - X_reconstructed
        scores = np.sum(diff * diff, axis=1)
        return scores.astype(np.float64)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable metadata describing fitted PCA model."""
        if not self.is_fitted:
            raise RuntimeError("Scorer not fitted.")

        return {
            "baseline": "B1_PCA",
            "name": "PCAScorer",
            "feature_mode": self.mode,
            "n_features": self.vectorizer.n_features,
            "k_components": self.k_components_,
            "target_variance_ratio": self.variance_ratio,
            "explained_variance_ratio": self.explained_variance_ratio_,
            "cumulative_explained_variance": self.cumulative_variance_,
            "random_state": self.random_state,
            "score_direction": "higher_is_more_anomalous",
        }


class IsolationForestScorer:
    """B1 Secondary / Diagnostic: Isolation Forest Anomaly Detector.

    Mathematical Formulation:
        1. Template count vectors x in R^D constructed from frozen training vocabulary.
        2. Isolation Forest fitted strictly on TRAIN vectors without labels.
        3. Anomaly score:
               Score_IF(x) = -score_samples(x)
           Since sklearn's score_samples returns negative numbers for anomalies and positive
           for normal, negating ensures higher score = more anomalous.
    """

    def __init__(
        self,
        mode: NormalizationMode = "normalized_count",
        n_estimators: int = 100,
        contamination: Any = "auto",
        random_state: int = 42,
    ):
        """Initialize IsolationForestScorer.

        Args:
            mode: Feature normalization mode.
            n_estimators: Number of trees in isolation forest.
            contamination: Assumed contamination rate ('auto' or float).
            random_state: Fixed random seed for reproducibility.
        """
        self.mode = mode
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

        self.vectorizer = TemplateCountVectorizer(mode=mode)
        self.model: Optional[IsolationForest] = None
        self.is_fitted = False

    def fit(self, windows: Sequence[LogWindow]) -> "IsolationForestScorer":
        """Fit vectorizer and Isolation Forest strictly on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        X_train = self.vectorizer.fit_transform(windows)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=1,  # CPU friendly deterministic single process
        )
        self.model.fit(X_train)

        self.is_fitted = True
        return self

    def score(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Compute negated isolation score (higher = more anomalous).

        Args:
            windows: Sequence of LogWindow instances.

        Returns:
            1D numpy array of anomaly scores (higher = more anomalous).
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("IsolationForestScorer must be fitted before scoring.")

        X = self.vectorizer.transform(windows)
        # sklearn score_samples is lower (negative) for anomalous samples.
        # Negate so higher = more anomalous.
        raw_scores = self.model.score_samples(X)
        scores = -raw_scores
        return scores.astype(np.float64)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable metadata describing fitted Isolation Forest model."""
        if not self.is_fitted:
            raise RuntimeError("Scorer not fitted.")

        return {
            "baseline": "B1_IsolationForest",
            "name": "IsolationForestScorer",
            "feature_mode": self.mode,
            "n_features": self.vectorizer.n_features,
            "n_estimators": self.n_estimators,
            "contamination": str(self.contamination),
            "random_state": self.random_state,
            "score_direction": "higher_is_more_anomalous",
        }
