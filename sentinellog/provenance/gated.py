"""Integration between Selective Prediction Gate and Phase 7 Citation Engine.

Extends the selective triage cascade:
    AUTO-CLEAR: No retrieval, no reranking, no provenance (zero search/audit cost).
    ESCALATE: Retrieval -> Reranking -> Provenance Citation Bundle.
"""

from typing import List, Optional, Sequence

from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.engine import ProvenanceEngine
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.retrieval.chunking import build_query_from_window
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.reranker import MMREvidenceReranker
from sentinellog.retrieval.reranking_schemas import (
    EvidenceSelectionResult,
    SelectedEvidence,
)
from sentinellog.retrieval.schemas import RetrievedEvidence


class GatedCitationResult:
    """Outcome of evaluating a window through gate, retrieval, reranking, and citation engine."""

    def __init__(
        self,
        window_id: str,
        score: float,
        decision: str,
        retrieval_invoked: bool,
        selection_invoked: bool,
        provenance_invoked: bool,
        retrieved_evidence: Optional[List[RetrievedEvidence]] = None,
        selected_evidence: Optional[List[SelectedEvidence]] = None,
        selection_result: Optional[EvidenceSelectionResult] = None,
        citation_bundle: Optional[CitationBundle] = None,
    ):
        self.window_id = window_id
        self.score = score
        self.decision = decision
        self.retrieval_invoked = retrieval_invoked
        self.selection_invoked = selection_invoked
        self.provenance_invoked = provenance_invoked
        self.retrieved_evidence = retrieved_evidence
        self.selected_evidence = selected_evidence
        self.selection_result = selection_result
        self.citation_bundle = citation_bundle

    def to_dict(self):
        return {
            "window_id": self.window_id,
            "score": self.score,
            "decision": self.decision,
            "retrieval_invoked": self.retrieval_invoked,
            "selection_invoked": self.selection_invoked,
            "provenance_invoked": self.provenance_invoked,
            "retrieved_evidence": (
                [e.to_dict() for e in self.retrieved_evidence]
                if self.retrieved_evidence is not None
                else None
            ),
            "selected_evidence": (
                [e.to_dict() for e in self.selected_evidence]
                if self.selected_evidence is not None
                else None
            ),
            "selection_result": (
                self.selection_result.to_dict()
                if self.selection_result is not None
                else None
            ),
            "citation_bundle": (
                self.citation_bundle.to_dict()
                if self.citation_bundle is not None
                else None
            ),
        }


class GatedCitationPipeline:
    """End-to-end triage cascade: Gate -> Retrieval -> Selection -> Citation."""

    def __init__(
        self,
        gate: SelectiveGate,
        retriever: IncidentRetriever,
        reranker: MMREvidenceReranker,
        provenance_engine: ProvenanceEngine,
    ):
        self.gate = gate
        self.retriever = retriever
        self.reranker = reranker
        self.provenance_engine = provenance_engine

    def process_window(
        self,
        window: LogWindow,
        score: float,
        retrieval_k: int = 5,
    ) -> GatedCitationResult:
        decision = self.gate.decide(score)

        if decision == "AUTO-CLEAR":
            return GatedCitationResult(
                window_id=window.window_id,
                score=float(score),
                decision="AUTO-CLEAR",
                retrieval_invoked=False,
                selection_invoked=False,
                provenance_invoked=False,
                retrieved_evidence=None,
                selected_evidence=None,
                selection_result=None,
                citation_bundle=None,
            )

        # Decision is "ESCALATE":
        # 1. Candidate Retrieval (Phase 5)
        candidates = self.retriever.retrieve(query=window, k=retrieval_k)

        # 2. Evidence Selection (Phase 6)
        query_obj = build_query_from_window(window)
        sel_result = self.reranker.rerank_and_select(
            query=query_obj,
            candidates=candidates,
            retrieval_k=retrieval_k,
        )

        # 3. Provenance Citation Bundle (Phase 7)
        bundle = self.provenance_engine.create_bundle(
            query_id=window.window_id,
            dataset=window.dataset,
            selected_evidence=sel_result.selected_evidence,
            verify=True,
        )

        return GatedCitationResult(
            window_id=window.window_id,
            score=float(score),
            decision="ESCALATE",
            retrieval_invoked=True,
            selection_invoked=True,
            provenance_invoked=True,
            retrieved_evidence=candidates,
            selected_evidence=sel_result.selected_evidence,
            selection_result=sel_result,
            citation_bundle=bundle,
        )
