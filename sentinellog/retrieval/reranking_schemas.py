"""Schemas for Phase 6 Retrieval Reranking and Evidence Selection.

Defines immutable, typed dataclasses for selected evidence chunks, selection results,
and gated pipeline outputs preserving original Phase 5 scores and provenance.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from sentinellog.retrieval.schemas import RetrievedEvidence


@dataclass
class SelectedEvidence:
    """A single evidence unit selected by Phase 6 reranking from Phase 5 candidates."""

    chunk_id: str
    source_window_id: str
    dataset: str
    split: str
    text: str
    record_count: int
    template_ids: List[int]
    retrieval_rank: int  # Original 1-indexed Phase 5 rank
    retrieval_score: float  # Original Phase 5 cosine similarity
    selected_rank: int  # 1-indexed Phase 6 selection order
    selection_score: float  # MMR selection score
    redundancy_penalty: float  # Max similarity to previously selected evidence (0.0 if first)
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    anomaly_label: bool = False  # Research diagnostic evaluation metadata only
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert selected evidence to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectedEvidence":
        """Instantiate selected evidence from dictionary."""
        return cls(**data)


@dataclass
class EvidenceSelectionResult:
    """The result of evidence reranking and selection for a single query."""

    query_id: str
    dataset: str
    candidate_count: int
    selected_count: int
    retrieval_k: int
    evidence_k: int
    mmr_lambda: float
    diversity_mode: str
    selected_evidence: List[SelectedEvidence]
    metrics: Dict[str, Any] = field(default_factory=dict)
    source_commit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        d = asdict(self)
        d["selected_evidence"] = [e.to_dict() for e in self.selected_evidence]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSelectionResult":
        """Instantiate result from dictionary."""
        ev_data = data.get("selected_evidence", [])
        ev_list = [SelectedEvidence.from_dict(e) for e in ev_data]
        return cls(
            query_id=data["query_id"],
            dataset=data["dataset"],
            candidate_count=data["candidate_count"],
            selected_count=data["selected_count"],
            retrieval_k=data["retrieval_k"],
            evidence_k=data["evidence_k"],
            mmr_lambda=data["mmr_lambda"],
            diversity_mode=data["diversity_mode"],
            selected_evidence=ev_list,
            metrics=data.get("metrics", {}),
            source_commit=data.get("source_commit"),
        )


@dataclass
class GatedEvidenceResult:
    """End-to-end outcome of evaluating a window through gate, retrieval, and reranking."""

    window_id: str
    score: float
    decision: str  # "AUTO-CLEAR" or "ESCALATE"
    retrieval_invoked: bool  # False for AUTO-CLEAR, True for ESCALATE
    selection_invoked: bool  # False for AUTO-CLEAR, True for ESCALATE
    retrieved_evidence: Optional[List[RetrievedEvidence]] = None  # Original Phase 5 candidates
    selected_evidence: Optional[List[SelectedEvidence]] = None  # Phase 6 selected evidence
    selection_result: Optional[EvidenceSelectionResult] = None  # Detailed result & diagnostics

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        d = {
            "window_id": self.window_id,
            "score": self.score,
            "decision": self.decision,
            "retrieval_invoked": self.retrieval_invoked,
            "selection_invoked": self.selection_invoked,
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
        }
        return d
