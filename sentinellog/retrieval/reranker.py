"""Deterministic evidence reranking and diversity-aware selection for Phase 6.

Implements Maximum Marginal Relevance (MMR) evidence selection over Phase 5 candidates:
    score(d) = lambda * relevance(d) - (1 - lambda) * max_{s in selected} sim(d, s)

Key Principles:
1. Label-Free: Anomaly labels are strictly forbidden from influencing ranking, lambda, or selection.
2. Deterministic Tie-Breaking: selection_score DESC, retrieval_score DESC, chunk_id ASC.
3. Preserves Phase 5 Signal: retrieval_score (cosine similarity) is preserved intact.
4. Redundancy Control: Evaluates candidate-to-selected pairwise similarity in embedding space.
5. Strict k Constraint: evidence_k <= retrieval_k enforced (fails explicitly if violated).
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from sentinellog.retrieval.embeddings import BaseEmbeddingModel
from sentinellog.retrieval.engine import cosine_similarity
from sentinellog.retrieval.guards import guard_query_does_not_contain_labels
from sentinellog.retrieval.reranking_schemas import (
    EvidenceSelectionResult,
    SelectedEvidence,
)
from sentinellog.retrieval.schemas import RetrievalQuery, RetrievedEvidence


class MMREvidenceReranker:
    """Deterministic MMR-style reranker and evidence selector."""

    def __init__(
        self,
        embedding_model: BaseEmbeddingModel,
        mmr_lambda: float = 0.70,
        evidence_k: int = 3,
        diversity_mode: str = "mmr",
    ):
        """Initialize MMR evidence reranker.

        Args:
            embedding_model: Fitted BaseEmbeddingModel for encoding candidates/evaluating diversity.
            mmr_lambda: Weight on relevance vs diversity in [0.0, 1.0].
                        1.0 = pure relevance, 0.0 = pure diversity.
            evidence_k: Target number of evidence chunks to select (must be >= 1).
            diversity_mode: Selection strategy name (default "mmr").
        """
        if not (0.0 <= mmr_lambda <= 1.0):
            raise ValueError(f"mmr_lambda must be in [0.0, 1.0], got {mmr_lambda}")
        if evidence_k < 1:
            raise ValueError(f"evidence_k must be at least 1, got {evidence_k}")

        self.embedding_model = embedding_model
        self.mmr_lambda = float(mmr_lambda)
        self.evidence_k = int(evidence_k)
        self.diversity_mode = diversity_mode

    def rerank_and_select(
        self,
        query: RetrievalQuery,
        candidates: Sequence[RetrievedEvidence],
        retrieval_k: Optional[int] = None,
        candidate_embeddings: Optional[np.ndarray] = None,
    ) -> EvidenceSelectionResult:
        """Rerank Phase 5 candidates using deterministic MMR and select a compact evidence set.

        Args:
            query: RetrievalQuery instance (label-free).
            candidates: Sequence of RetrievedEvidence objects from Phase 5 retrieval.
            retrieval_k: Number of retrieved candidates requested in Phase 5.
                         If None, inferred as len(candidates).
            candidate_embeddings: Optional precomputed 2D numpy array of shape (len(candidates), dim).
                                 If None, candidate texts will be encoded using self.embedding_model.

        Returns:
            EvidenceSelectionResult containing the selected evidence, scores, and diagnostics.
        """
        # Guard: Query must not contain anomaly labels
        guard_query_does_not_contain_labels(query)

        n_candidates = len(candidates)
        if retrieval_k is not None:
            if self.evidence_k > retrieval_k:
                raise ValueError(
                    f"Configuration constraint violated: evidence_k ({self.evidence_k}) "
                    f"cannot exceed retrieval_k ({retrieval_k})."
                )
            inferred_retrieval_k = retrieval_k
        else:
            inferred_retrieval_k = n_candidates

        target_k = min(self.evidence_k, n_candidates)

        if n_candidates == 0 or target_k == 0:
            return EvidenceSelectionResult(
                query_id=query.query_window_id,
                dataset=query.dataset,
                candidate_count=0,
                selected_count=0,
                retrieval_k=inferred_retrieval_k,
                evidence_k=self.evidence_k,
                mmr_lambda=self.mmr_lambda,
                diversity_mode=self.diversity_mode,
                selected_evidence=[],
                metrics={
                    "compression_ratio": 0.0,
                    "mean_candidate_similarity": 0.0,
                    "mean_selected_similarity": 0.0,
                    "mean_pairwise_candidate_similarity": 0.0,
                    "mean_pairwise_selected_similarity": 0.0,
                    "max_pairwise_selected_similarity": 0.0,
                    "unique_source_window_count": 0,
                    "duplicate_chunk_count": 0,
                },
            )


        # Obtain candidate embeddings for redundancy measurement
        if candidate_embeddings is not None:
            cand_vecs = np.asarray(candidate_embeddings, dtype=np.float32)
            if len(cand_vecs) != n_candidates:
                raise ValueError(
                    f"Candidate embeddings count ({len(cand_vecs)}) does not match "
                    f"candidates count ({n_candidates})."
                )
        else:
            cand_texts = [c.text for c in candidates]
            cand_vecs = self.embedding_model.encode(cand_texts)

        # Precompute pairwise similarity matrix among candidates
        # Shape: (N, N)
        norms = np.linalg.norm(cand_vecs, axis=1, keepdims=True)
        # Safe zero-norm handling
        safe_norms = np.where(norms == 0.0, 1.0, norms)
        normalized_vecs = np.where(norms == 0.0, 0.0, cand_vecs / safe_norms)
        pairwise_sim_matrix = np.dot(normalized_vecs, normalized_vecs.T)
        # Clip numerical tolerances to [-1.0, 1.0]
        pairwise_sim_matrix = np.clip(pairwise_sim_matrix, -1.0, 1.0)

        # Candidate relevance scores from Phase 5 (preserved intact)
        relevance_scores = [float(c.similarity) for c in candidates]

        # Greedy MMR selection loop
        selected_indices: List[int] = []
        selected_scores: List[float] = []
        selected_penalties: List[float] = []
        remaining_indices = list(range(n_candidates))

        for step in range(target_k):
            best_idx: Optional[int] = None
            best_score = float("-inf")
            best_penalty = 0.0

            # Find candidate maximizing MMR score with deterministic tie-breaking
            # Candidate tie-breaker: selection_score DESC, retrieval_score DESC, chunk_id ASC
            candidates_scored = []
            for idx in remaining_indices:
                rel = relevance_scores[idx]
                if len(selected_indices) == 0:
                    # For first item, no redundancy penalty exists
                    # Standard MMR convention: score = relevance
                    penalty = 0.0
                    mmr_score = rel
                else:
                    # Max similarity to any previously selected item
                    penalty = float(max(pairwise_sim_matrix[idx, s_idx] for s_idx in selected_indices))
                    mmr_score = float(self.mmr_lambda * rel - (1.0 - self.mmr_lambda) * penalty)

                candidates_scored.append((idx, mmr_score, rel, penalty, candidates[idx].chunk_id))

            # Deterministic sort:
            # (-mmr_score, -retrieval_score, chunk_id)
            candidates_scored.sort(
                key=lambda item: (-item[1], -item[2], item[4])
            )

            chosen = candidates_scored[0]
            chosen_idx, chosen_score, _, chosen_penalty, _ = chosen

            selected_indices.append(chosen_idx)
            selected_scores.append(chosen_score)
            selected_penalties.append(chosen_penalty)
            remaining_indices.remove(chosen_idx)

        # Build SelectedEvidence objects
        selected_evidence: List[SelectedEvidence] = []
        for rank, (idx, sel_score, penalty) in enumerate(
            zip(selected_indices, selected_scores, selected_penalties), start=1
        ):
            cand = candidates[idx]
            selected_evidence.append(
                SelectedEvidence(
                    chunk_id=cand.chunk_id,
                    source_window_id=cand.source_window_id,
                    dataset=cand.dataset,
                    split=cand.split,
                    text=cand.text,
                    record_count=cand.record_count,
                    template_ids=list(cand.template_ids),
                    retrieval_rank=cand.rank,
                    retrieval_score=cand.similarity,
                    selected_rank=rank,
                    selection_score=sel_score,
                    redundancy_penalty=penalty,
                    timestamp_start=cand.timestamp_start,
                    timestamp_end=cand.timestamp_end,
                    anomaly_label=cand.anomaly_label,
                    provenance=dict(cand.provenance),
                )
            )

        # Compute selection diagnostics
        metrics = self._compute_selection_metrics(
            candidates=candidates,
            selected_indices=selected_indices,
            pairwise_matrix=pairwise_sim_matrix,
            inferred_retrieval_k=inferred_retrieval_k,
        )

        return EvidenceSelectionResult(
            query_id=query.query_window_id,
            dataset=query.dataset,
            candidate_count=n_candidates,
            selected_count=len(selected_evidence),
            retrieval_k=inferred_retrieval_k,
            evidence_k=self.evidence_k,
            mmr_lambda=self.mmr_lambda,
            diversity_mode=self.diversity_mode,
            selected_evidence=selected_evidence,
            metrics=metrics,
        )

    def _compute_selection_metrics(
        self,
        candidates: Sequence[RetrievedEvidence],
        selected_indices: List[int],
        pairwise_matrix: np.ndarray,
        inferred_retrieval_k: int,
    ) -> Dict[str, Any]:
        """Compute diversity, redundancy, and compression diagnostic metrics."""
        n_cands = len(candidates)
        n_selected = len(selected_indices)

        cand_sims = [c.similarity for c in candidates]
        mean_cand_sim = float(np.mean(cand_sims)) if cand_sims else 0.0

        selected_sims = [candidates[i].similarity for i in selected_indices]
        mean_sel_sim = float(np.mean(selected_sims)) if selected_sims else 0.0

        # Pairwise candidate similarities (upper triangle off-diagonal)
        if n_cands > 1:
            cand_triu = pairwise_matrix[np.triu_indices(n_cands, k=1)]
            mean_cand_pairwise = float(np.mean(cand_triu)) if len(cand_triu) > 0 else 0.0
        else:
            mean_cand_pairwise = 0.0

        # Pairwise selected similarities
        if n_selected > 1:
            sel_submatrix = pairwise_matrix[np.ix_(selected_indices, selected_indices)]
            sel_triu = sel_submatrix[np.triu_indices(n_selected, k=1)]
            mean_sel_pairwise = float(np.mean(sel_triu)) if len(sel_triu) > 0 else 0.0
            max_sel_pairwise = float(np.max(sel_triu)) if len(sel_triu) > 0 else 0.0
        else:
            mean_sel_pairwise = 0.0
            max_sel_pairwise = 0.0

        # Source window diversity
        unique_windows = len({candidates[i].source_window_id for i in selected_indices})
        unique_chunks = len({candidates[i].chunk_id for i in selected_indices})
        duplicate_chunks = n_selected - unique_chunks

        compression_ratio = float(n_selected / inferred_retrieval_k) if inferred_retrieval_k > 0 else 0.0

        return {
            "compression_ratio": round(compression_ratio, 4),
            "mean_candidate_similarity": round(mean_cand_sim, 4),
            "mean_selected_similarity": round(mean_sel_sim, 4),
            "relevance_delta": round(mean_sel_sim - mean_cand_sim, 4),
            "mean_pairwise_candidate_similarity": round(mean_cand_pairwise, 4),
            "mean_pairwise_selected_similarity": round(mean_sel_pairwise, 4),
            "max_pairwise_selected_similarity": round(max_sel_pairwise, 4),
            "pairwise_similarity_reduction": round(mean_cand_pairwise - mean_sel_pairwise, 4),
            "unique_source_window_count": unique_windows,
            "unique_chunk_count": unique_chunks,
            "duplicate_chunk_count": duplicate_chunks,
        }
