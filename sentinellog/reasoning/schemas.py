"""Data schemas and typed models for Phase 8 Incident Reasoning Engine.

Defines immutable, typed dataclasses for:
- Evidence contributions
- Deterministic signals
- Incident rules
- Reasoning traces
- Incident assessments
- Reasoning results and summaries
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class IncidentDecision(str, Enum):
    """Deterministic reasoning decision taxonomy."""
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    INCIDENT = "INCIDENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class IncidentSeverity(str, Enum):
    """Deterministic incident severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContributionType(str, Enum):
    """Deterministic evidence contribution classification."""
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    CONTEXTUAL = "CONTEXTUAL"
    INSUFFICIENT = "INSUFFICIENT"


class SufficiencyStatus(str, Enum):
    """Deterministic evidence sufficiency classification."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class ProvenanceStatus(str, Enum):
    """Status of citation provenance verification."""
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class IncidentSignal:
    """A deterministic numerical or categorical signal extracted from pipeline outputs."""

    name: str
    value: Any
    normalized_value: float  # [0.0, 1.0] scale
    strength: str  # 'LOW', 'MEDIUM', 'HIGH'
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentSignal":
        return cls(**data)


@dataclass(frozen=True)
class EvidenceContribution:
    """Deterministic contribution record for a single selected evidence citation."""

    citation_id: str
    chunk_id: str
    relevance_score: float
    redundancy_score: float
    contribution_type: str  # 'SUPPORTING', 'CONTRADICTING', 'CONTEXTUAL', 'INSUFFICIENT'
    contribution_strength: str  # 'LOW', 'MEDIUM', 'HIGH'
    provenance_status: str  # 'VERIFIED', 'INVALID', 'UNRESOLVED'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceContribution":
        return cls(**data)


@dataclass(frozen=True)
class IncidentRule:
    """An explicit, inspectable deterministic reasoning rule."""

    rule_id: str
    description: str
    inputs: List[str]
    condition: str
    output: str
    priority: int  # Lower number = higher priority

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentRule":
        return cls(**data)


@dataclass
class ReasoningTrace:
    """Auditable machine-readable trace recording exactly why a decision was reached."""

    rules_evaluated: List[str]
    rules_fired: List[str]
    signals: Dict[str, Any]
    evidence_used: List[str]
    conflicts: List[Dict[str, Any]]
    final_decision: str
    final_severity: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningTrace":
        return cls(**data)


@dataclass
class IncidentAssessment:
    """Structured, reproducible outcome of deterministic incident reasoning for a window."""

    dataset: str
    split: str
    window_id: str
    session_id: Optional[str]
    decision: str  # 'NORMAL', 'SUSPICIOUS', 'INCIDENT', 'INSUFFICIENT_EVIDENCE'
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    confidence: float  # [0.0, 1.0] reasoning support strength (not a probability)
    signal_summary: Dict[str, Any]
    evidence_contributions: List[EvidenceContribution]
    reasoning_trace: ReasoningTrace
    citation_ids: List[str]
    provenance_status: str  # 'VERIFIED', 'INVALID', 'UNAVAILABLE'
    engine_version: str
    configuration_hash: str
    created_timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "split": self.split,
            "window_id": self.window_id,
            "session_id": self.session_id,
            "decision": self.decision,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "signal_summary": self.signal_summary,
            "evidence_contributions": [c.to_dict() for c in self.evidence_contributions],
            "reasoning_trace": self.reasoning_trace.to_dict(),
            "citation_ids": list(self.citation_ids),
            "provenance_status": self.provenance_status,
            "engine_version": self.engine_version,
            "configuration_hash": self.configuration_hash,
            "created_timestamp": self.created_timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentAssessment":
        return cls(
            dataset=data["dataset"],
            split=data["split"],
            window_id=data["window_id"],
            session_id=data.get("session_id"),
            decision=data["decision"],
            severity=data["severity"],
            confidence=float(data["confidence"]),
            signal_summary=data.get("signal_summary", {}),
            evidence_contributions=[
                EvidenceContribution.from_dict(c)
                for c in data.get("evidence_contributions", [])
            ],
            reasoning_trace=ReasoningTrace.from_dict(data["reasoning_trace"]),
            citation_ids=list(data.get("citation_ids", [])),
            provenance_status=data["provenance_status"],
            engine_version=data["engine_version"],
            configuration_hash=data["configuration_hash"],
            created_timestamp=data.get("created_timestamp"),
        )


@dataclass
class ReasoningResult:
    """Container returned by ReasoningEngine for a processed query window."""

    assessment: IncidentAssessment
    raw_window_id: str
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment": self.assessment.to_dict(),
            "raw_window_id": self.raw_window_id,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class ReasoningSummary:
    """Dataset-level summary of reasoning results, distributions, and diagnostic metrics."""

    dataset: str
    split: str
    engine_version: str
    configuration_hash: str
    total_assessed: int
    decision_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    sufficiency_distribution: Dict[str, int]
    provenance_status_distribution: Dict[str, int]
    conflict_count: int
    conflict_rate: float
    average_evidence_count: float
    average_evidence_relevance: float
    average_confidence: float
    rule_firing_frequencies: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningSummary":
        return cls(**data)
