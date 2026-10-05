"""Integration between Selective Prediction Gate and Phase 5 Retrieval Engine.

Enforces the central research principle:
    - Normal / low-risk windows that receive AUTO-CLEAR bypass retrieval entirely.
    - Only windows that receive ESCALATE invoke the contextual retrieval engine.
"""

from typing import List, Optional, Sequence

from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.chunking import build_query_from_window
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.reranker import MMREvidenceReranker
from sentinellog.retrieval.reranking_schemas import GatedEvidenceResult
from sentinellog.retrieval.schemas import GatedRetrievalResult


class GatedRetrievalPipeline:
    """End-to-end pipeline connecting calibrated selective escalation to contextual retrieval."""

    def __init__(self, gate: SelectiveGate, retriever: IncidentRetriever):
        """Initialize gated pipeline.

        Args:
            gate: Calibrated SelectiveGate instance.
            retriever: IncidentRetriever instance holding the TRAIN corpus index.
        """
        self.gate = gate
        self.retriever = retriever

    def process_window(
        self,
        window: LogWindow,
        score: float,
        k: int = 5,
    ) -> GatedRetrievalResult:
        """Process a single log window through selective gate and conditional retrieval.

        Args:
            window: LogWindow to triage.
            score: Calibrated nonconformity anomaly score.
            k: Top-k evidence chunks to retrieve if escalated.

        Returns:
            GatedRetrievalResult containing decision, retrieval invocation flag, and evidence.
        """
        decision = self.gate.decide(score)

        if decision == "AUTO-CLEAR":
            return GatedRetrievalResult(
                window_id=window.window_id,
                score=float(score),
                decision="AUTO-CLEAR",
                retrieval_invoked=False,
                retrieved_evidence=None,
            )

        # Decision is "ESCALATE": Invoke retrieval over historical TRAIN incidents
        evidence = self.retriever.retrieve(query=window, k=k)
        return GatedRetrievalResult(
            window_id=window.window_id,
            score=float(score),
            decision="ESCALATE",
            retrieval_invoked=True,
            retrieved_evidence=evidence,
        )

    def process_batch(
        self,
        windows: Sequence[LogWindow],
        scores: Sequence[float],
        k: int = 5,
    ) -> List[GatedRetrievalResult]:
        """Process a batch of log windows through selective gating and conditional retrieval."""
        if len(windows) != len(scores):
            raise ValueError(
                f"Mismatch between windows count ({len(windows)}) and scores count ({len(scores)})"
            )

        return [
            self.process_window(w, s, k=k)
            for w, s in zip(windows, scores)
        ]


class GatedEvidencePipeline:
    """End-to-end cascade connecting Selective Gate -> Phase 5 Retrieval -> Phase 6 Reranking."""

    def __init__(
        self,
        gate: SelectiveGate,
        retriever: IncidentRetriever,
        reranker: MMREvidenceReranker,
    ):
        """Initialize gated evidence pipeline.

        Args:
            gate: Calibrated SelectiveGate instance.
            retriever: IncidentRetriever instance holding the TRAIN corpus index.
            reranker: MMREvidenceReranker instance for diversity-aware evidence selection.
        """
        self.gate = gate
        self.retriever = retriever
        self.reranker = reranker

    def process_window(
        self,
        window: LogWindow,
        score: float,
        retrieval_k: int = 5,
    ) -> GatedEvidenceResult:
        """Process a single log window through gate, retrieval, and reranking.

        Flow:
            AUTO-CLEAR: No retrieval, no reranking, no evidence selection.
            ESCALATE: Retrieval (retrieval_k candidates) -> Reranking (evidence_k selected).

        Args:
            window: LogWindow to triage.
            score: Calibrated nonconformity anomaly score.
            retrieval_k: Number of candidate chunks to retrieve if escalated.

        Returns:
            GatedEvidenceResult containing decision, candidate evidence, and selected evidence.
        """
        decision = self.gate.decide(score)

        if decision == "AUTO-CLEAR":
            return GatedEvidenceResult(
                window_id=window.window_id,
                score=float(score),
                decision="AUTO-CLEAR",
                retrieval_invoked=False,
                selection_invoked=False,
                retrieved_evidence=None,
                selected_evidence=None,
                selection_result=None,
            )

        # Decision is "ESCALATE":
        # 1. Candidate Retrieval (Phase 5)
        candidates = self.retriever.retrieve(query=window, k=retrieval_k)

        # 2. Evidence Reranking & Selection (Phase 6)
        query_obj = build_query_from_window(window)
        sel_result = self.reranker.rerank_and_select(
            query=query_obj,
            candidates=candidates,
            retrieval_k=retrieval_k,
        )

        return GatedEvidenceResult(
            window_id=window.window_id,
            score=float(score),
            decision="ESCALATE",
            retrieval_invoked=True,
            selection_invoked=True,
            retrieved_evidence=candidates,
            selected_evidence=sel_result.selected_evidence,
            selection_result=sel_result,
        )

    def process_batch(
        self,
        windows: Sequence[LogWindow],
        scores: Sequence[float],
        retrieval_k: int = 5,
    ) -> List[GatedEvidenceResult]:
        """Process a batch of log windows through gated evidence cascade."""
        if len(windows) != len(scores):
            raise ValueError(
                f"Mismatch between windows count ({len(windows)}) and scores count ({len(scores)})"
            )

        return [
            self.process_window(w, s, retrieval_k=retrieval_k)
            for w, s in zip(windows, scores)
        ]
