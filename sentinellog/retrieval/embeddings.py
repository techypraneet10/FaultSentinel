"""Deterministic local embedding abstraction and implementation for Phase 5 retrieval.

Provides a reproducible, CPU-efficient, local embedding model that fits strictly on TRAIN data
and operates with zero external APIs, zero network calls, and zero API keys.
"""

from abc import ABC, abstractmethod
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from sentinellog.retrieval.guards import guard_train_split_only
from sentinellog.scoring.artifacts import get_git_commit_sha


class BaseEmbeddingModel(ABC):
    """Abstract base class for deterministic local embedding models."""

    @abstractmethod
    def fit(self, texts: Sequence[str], split: str = "train") -> "BaseEmbeddingModel":
        """Fit vocabulary and parameters strictly on TRAIN texts."""
        pass

    @abstractmethod
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode texts into L2-normalized float32 vectors.

        Returns:
            np.ndarray of shape (len(texts), dimension), float32.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimensionality."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Unique identifier for the embedding model."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version string."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return provenance metadata."""
        pass


class TemplateTfidfEmbeddingModel(BaseEmbeddingModel):
    """Deterministic local TF-IDF embedding model over log template tokens.

    Key Properties:
        - Trained strictly on TRAIN partition under Rule 1.
        - L2-normalized vectors guarantee cosine similarity via dot product.
        - Safe zero-vector handling for empty or out-of-vocabulary queries (no NaN/Inf).
        - Fully deterministic vocabulary and inverse document frequency statistics.
    """

    def __init__(self, source_commit: Optional[str] = None):
        """Initialize embedding model."""
        self._model_name = "template_tfidf_v1"
        self._version = "1.0.0"
        self._source_commit = source_commit or get_git_commit_sha()
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_fitted: bool = False
        self._dimension: int = 0
        self._vocabulary_hash: str = ""
        self._fitting_split: str = ""

    @property
    def dimension(self) -> int:
        if not self.is_fitted:
            raise RuntimeError("Embedding model has not been fitted.")
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def version(self) -> str:
        return self._version

    @property
    def vocabulary_hash(self) -> str:
        if not self.is_fitted:
            raise RuntimeError("Embedding model has not been fitted.")
        return self._vocabulary_hash

    def fit(self, texts: Sequence[str], split: str = "train") -> "TemplateTfidfEmbeddingModel":
        """Fit TF-IDF vocabulary strictly on TRAIN texts.

        Args:
            texts: Sequence of template token strings from TRAIN.
            split: Partition name (strictly 'train').

        Returns:
            self
        """
        guard_train_split_only(split)

        if not texts:
            raise ValueError("Cannot fit embedding model on an empty text collection.")

        # Token pattern matches whitespace-separated template tokens (preserving underscores)
        self.vectorizer = TfidfVectorizer(
            token_pattern=r"\S+",
            norm="l2",
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=False,
        )

        self.vectorizer.fit(texts)
        self.is_fitted = True
        self._fitting_split = split
        self._dimension = len(self.vectorizer.vocabulary_)

        # Compute deterministic SHA-256 of sorted vocabulary
        sorted_vocab = sorted(self.vectorizer.vocabulary_.items(), key=lambda x: x[0])
        vocab_bytes = json.dumps(sorted_vocab).encode("utf-8")
        self._vocabulary_hash = hashlib.sha256(vocab_bytes).hexdigest()

        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode texts into L2-normalized float32 vectors.

        Args:
            texts: Sequence of template token strings.

        Returns:
            2D numpy array of shape (N, dimension), dtype float32.
        """
        if not self.is_fitted or self.vectorizer is None:
            raise RuntimeError("TemplateTfidfEmbeddingModel must be fitted before encoding.")

        if len(texts) == 0:
            return np.empty((0, self._dimension), dtype=np.float32)

        # Transform using frozen vocabulary
        sparse_mat = self.vectorizer.transform(texts)
        dense_arr = sparse_mat.toarray().astype(np.float32)

        # Verify numerical safety: strictly no NaN or Inf
        if np.isnan(dense_arr).any() or np.isinf(dense_arr).any():
            dense_arr = np.nan_to_num(dense_arr, nan=0.0, posinf=0.0, neginf=0.0)

        # Scikit-learn norm='l2' leaves all-zero rows with norm 0.0 (safe).
        # Double check non-zero rows are L2 normalized
        norms = np.linalg.norm(dense_arr, axis=1, keepdims=True)
        nonzero = (norms > 0.0).flatten()
        if np.any(nonzero):
            dense_arr[nonzero] = dense_arr[nonzero] / norms[nonzero]

        return dense_arr

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable provenance metadata."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")

        return {
            "model_name": self._model_name,
            "version": self._version,
            "dimension": self._dimension,
            "vocabulary_hash": self._vocabulary_hash,
            "vocabulary_size": len(self.vectorizer.vocabulary_) if self.vectorizer else 0,
            "fitting_split": self._fitting_split,
            "source_commit": self._source_commit,
            "norm": "l2",
            "metric": "cosine",
        }
