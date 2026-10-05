"""Deterministic cosine similarity retrieval engine for Phase 5 incident triage.

Retrieves top-k historical TRAIN evidence chunks for escalated query log windows.
Enforces:
1. Searching strictly over the TRAIN corpus.
2. Self-retrieval exclusion when the query is from TRAIN.
3. Same-dataset filtering (HDFS vs BGL isolation).
4. Strictly deterministic tie-breaking (similarity DESC, chunk_id ASC).
"""

from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.chunking import build_query_from_window
from sentinellog.retrieval.embeddings import BaseEmbeddingModel
from sentinellog.retrieval.guards import (
    guard_query_does_not_contain_labels,
    guard_train_split_only,
)
from sentinellog.retrieval.schemas import (
    RetrievalChunk,
    RetrievalQuery,
    RetrievedEvidence,
)


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors with safe zero-norm handling.

    Args:
        v1: 1D numpy array.
        v2: 1D numpy array.

    Returns:
        Float cosine similarity in [-1.0, 1.0]. Returns 0.0 if either vector has norm 0.
    """
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    dot = float(np.dot(v1, v2))
    val = dot / (n1 * n2)
    return float(max(-1.0, min(1.0, val)))


def batch_cosine_similarities(query_vec: np.ndarray, corpus_vecs: np.ndarray) -> np.ndarray:
    """Compute cosine similarities between a single query vector and a matrix of corpus vectors.

    Args:
        query_vec: 1D numpy array of shape (d,).
        corpus_vecs: 2D numpy array of shape (N, d).

    Returns:
        1D numpy array of shape (N,), dtype float32, in [-1.0, 1.0].
    """
    if len(corpus_vecs) == 0:
        return np.empty((0,), dtype=np.float32)

    norm_q = float(np.linalg.norm(query_vec))
    if norm_q == 0.0:
        return np.zeros(len(corpus_vecs), dtype=np.float32)

    norms_corpus = np.linalg.norm(corpus_vecs, axis=1)
    dots = np.dot(corpus_vecs, query_vec)

    sims = np.zeros(len(corpus_vecs), dtype=np.float32)
    valid = norms_corpus > 0.0
    sims[valid] = (dots[valid] / (norms_corpus[valid] * norm_q)).astype(np.float32)

    return np.clip(sims, -1.0, 1.0)


class IncidentRetriever:
    """Deterministic retrieval engine over historical TRAIN incident chunks."""

    def __init__(
        self,
        corpus: Sequence[RetrievalChunk],
        corpus_embeddings: np.ndarray,
        embedding_model: BaseEmbeddingModel,
        dataset: str,
        same_dataset_only: bool = True,
        exclude_self: bool = True,
    ):
        """Initialize retriever.

        Args:
            corpus: Sequence of RetrievalChunk instances from TRAIN.
            corpus_embeddings: 2D array of corpus embeddings.
            embedding_model: Fitted BaseEmbeddingModel instance.
            dataset: Target dataset name ('hdfs' or 'bgl').
            same_dataset_only: If True, restricts retrieval to chunks matching query dataset.
            exclude_self: If True, excludes the query's own source window from results.
        """
        # Enforce that every corpus record is strictly from TRAIN
        for chunk in corpus:
            guard_train_split_only(chunk.split)

        if len(corpus) != len(corpus_embeddings):
            raise ValueError(
                f"Corpus size ({len(corpus)}) does not match embeddings count ({len(corpus_embeddings)})"
            )

        self.corpus = list(corpus)
        self.corpus_embeddings = np.asarray(corpus_embeddings, dtype=np.float32)
        self.embedding_model = embedding_model
        self.dataset = dataset.strip().lower()
        self.same_dataset_only = same_dataset_only
        self.exclude_self = exclude_self

    def retrieve(
        self,
        query: Union[RetrievalQuery, LogWindow],
        k: int = 5,
        exclude_source_id: Optional[str] = None,
    ) -> List[RetrievedEvidence]:
        """Retrieve top-k historical TRAIN chunks for a query.

        Args:
            query: RetrievalQuery instance or raw LogWindow.
            k: Number of nearest neighbors to retrieve (default 5).
            exclude_source_id: Optional window ID to explicitly exclude.

        Returns:
            Ranked list of RetrievedEvidence instances sorted by similarity DESC, chunk_id ASC.
        """
        if k <= 0:
            return []

        # Convert LogWindow if passed directly
        if isinstance(query, LogWindow):
            q_obj = build_query_from_window(query)
            target_source_id = exclude_source_id or query.window_id
        else:
            q_obj = query
            target_source_id = exclude_source_id or q_obj.query_window_id

        guard_query_does_not_contain_labels(q_obj)

        if len(self.corpus) == 0:
            return []

        # Encode query text
        q_vec = self.embedding_model.encode([q_obj.text])[0]

        # Compute batch similarities against corpus
        sims = batch_cosine_similarities(q_vec, self.corpus_embeddings)

        # Filter candidates
        candidates = []
        for idx, (sim, chunk) in enumerate(zip(sims, self.corpus)):
            # Dataset filter
            if self.same_dataset_only and chunk.dataset.strip().lower() != q_obj.dataset.strip().lower():
                continue

            # Self-retrieval exclusion
            if self.exclude_self and chunk.source_window_id == target_source_id:
                continue

            candidates.append((float(sim), chunk))

        # Deterministic sorting: similarity DESC, chunk_id ASC
        candidates.sort(key=lambda item: (-item[0], item[1].chunk_id))

        top_candidates = candidates[:k]

        evidence_list: List[RetrievedEvidence] = []
        for rank, (sim, chunk) in enumerate(top_candidates, start=1):
            evidence_list.append(
                RetrievedEvidence(
                    rank=rank,
                    similarity=sim,
                    chunk_id=chunk.chunk_id,
                    source_window_id=chunk.source_window_id,
                    dataset=chunk.dataset,
                    split=chunk.split,
                    text=chunk.text,
                    record_count=chunk.record_count,
                    template_ids=list(chunk.template_ids),
                    timestamp_start=chunk.timestamp_start,
                    timestamp_end=chunk.timestamp_end,
                    anomaly_label=chunk.anomaly_label,
                    provenance=chunk.provenance,
                )
            )

        return evidence_list
