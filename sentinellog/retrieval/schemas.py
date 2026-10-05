"""Data schemas and types for Phase 5 retrieval infrastructure.

Defines typed dataclasses for retrieval chunks, queries, retrieved evidence sets,
and gated retrieval outcomes.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetrievalChunk:
    """Historical context unit derived strictly from a TRAIN log window."""

    chunk_id: str  # Deterministic SHA-256 hash of dataset, split, source_window_id, text
    dataset: str
    split: str  # Invariant: must be "train"
    source_window_id: str
    session_id: Optional[str] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    record_count: int = 0
    template_ids: List[int] = field(default_factory=list)
    text: str = ""  # Observable template representation, NO ground-truth labels
    anomaly_label: bool = False  # Stored purely as corpus metadata for research evaluation
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalChunk":
        """Instantiate chunk from dictionary."""
        return cls(**data)


@dataclass
class RetrievedEvidence:
    """A ranked historical TRAIN chunk retrieved for an escalated query window."""

    rank: int  # 1-indexed rank
    similarity: float  # Cosine similarity in [-1.0, 1.0]
    chunk_id: str
    source_window_id: str
    dataset: str
    split: str
    text: str
    record_count: int
    template_ids: List[int]
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    anomaly_label: bool = False  # Diagnostic evaluation metadata only
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievedEvidence":
        """Instantiate evidence from dictionary."""
        return cls(**data)


@dataclass
class RetrievalQuery:
    """Search query constructed deterministically from an escalated window."""

    query_window_id: str
    dataset: str
    record_count: int
    template_ids: List[int]
    text: str  # Observable template representation, NO ground-truth labels

    def to_dict(self) -> Dict[str, Any]:
        """Convert query to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalQuery":
        """Instantiate query from dictionary."""
        return cls(**data)


@dataclass
class GatedRetrievalResult:
    """Outcome of evaluating a window through the selective gate and retrieval engine."""

    window_id: str
    score: float
    decision: str  # "AUTO-CLEAR" or "ESCALATE"
    retrieval_invoked: bool  # False for AUTO-CLEAR, True for ESCALATE
    retrieved_evidence: Optional[List[RetrievedEvidence]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        d = asdict(self)
        if self.retrieved_evidence is not None:
            d["retrieved_evidence"] = [e.to_dict() for e in self.retrieved_evidence]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatedRetrievalResult":
        """Instantiate result from dictionary."""
        ev_data = data.get("retrieved_evidence")
        ev_list = [RetrievedEvidence.from_dict(e) for e in ev_data] if ev_data is not None else None
        return cls(
            window_id=data["window_id"],
            score=data["score"],
            decision=data["decision"],
            retrieval_invoked=data["retrieval_invoked"],
            retrieved_evidence=ev_list,
        )
