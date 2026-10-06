"""Data schemas and typed models for Phase 9 LLM Explanation & Orchestration.

Defines immutable, typed dataclasses and taxonomy enums for:
- Explanation citations
- Explanation claims and taxonomy
- Faithfulness and grounding evaluation records
- Validation traces and results
- LLM runtime usage metadata
- Complete structured ExplanationResult
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence


class ClaimType(str, Enum):
    """Fixed vocabulary for claim classification."""
    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    CORRELATION = "CORRELATION"
    INTERPRETATION = "INTERPRETATION"
    UNCERTAINTY = "UNCERTAINTY"
    RECOMMENDATION = "RECOMMENDATION"

    @classmethod
    def is_factual(cls, claim_type: str) -> bool:
        """Return True if claim type is an externally verifiable factual assertion."""
        normalized = str(claim_type).strip().upper()
        return normalized in {cls.OBSERVATION.value, cls.EVIDENCE.value, cls.CORRELATION.value}


class FaithfulnessStatus(str, Enum):
    """Status of programmatic grounding and faithfulness evaluation."""
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"
    NOT_EVALUATED = "NOT_EVALUATED"


class ExplanationStatus(str, Enum):
    """Lifecycle status of the generated explanation."""
    GENERATED = "GENERATED"
    ABSTAINED = "ABSTAINED"
    INVALID = "INVALID"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class CitationValidationStatus(str, Enum):
    """Status of citation integrity validation against Phase 7 bundles."""
    VALID = "VALID"
    INVALID = "INVALID"
    UNCHECKED = "UNCHECKED"


@dataclass(frozen=True)
class LLMUsageMetadata:
    """Runtime telemetry and resource consumption for LLM invocation."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMUsageMetadata":
        return cls(**data)


@dataclass(frozen=True)
class ExplanationCitation:
    """Structured citation representation bound to a Phase 7 citation bundle entry."""
    citation_id: str
    citation_text: str
    chunk_id: str
    source_window_id: str
    dataset: str
    split: str
    selected_rank: int
    retrieval_score: float
    selection_score: float
    provenance_status: str
    source_location: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplanationCitation":
        return cls(**data)


@dataclass
class ExplanationClaim:
    """An individual atomic statement extracted from an explanation."""
    claim_id: str
    text: str
    claim_type: str  # One of ClaimType enum values
    citation_ids: List[str] = field(default_factory=list)
    is_factual: bool = True
    supported: bool = False
    support_score: float = 0.0
    validation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplanationClaim":
        return cls(**data)


@dataclass
class FaithfulnessResult:
    """Outcome of programmatic faithfulness and grounding checks."""
    status: str  # One of FaithfulnessStatus values
    grounding_score: float  # [0.0, 1.0] empirical grounding signal
    claims_checked: int = 0
    claims_supported: int = 0
    numeric_checks_passed: bool = True
    unsupported_claims: List[str] = field(default_factory=list)
    contradictions_detected: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaithfulnessResult":
        return cls(**data)


@dataclass
class ValidationResult:
    """Comprehensive outcome of multi-stage output verification."""
    is_valid: bool
    citation_status: str  # One of CitationValidationStatus values
    decision_consistent: bool
    severity_consistent: bool
    numeric_consistent: bool
    citation_coverage: float  # supported factual claims / total factual claims
    citation_precision: float  # valid cited evidence refs / total cited evidence refs
    faithfulness_result: FaithfulnessResult
    validation_trace: List[Dict[str, Any]] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "citation_status": self.citation_status,
            "decision_consistent": self.decision_consistent,
            "severity_consistent": self.severity_consistent,
            "numeric_consistent": self.numeric_consistent,
            "citation_coverage": round(self.citation_coverage, 4),
            "citation_precision": round(self.citation_precision, 4),
            "faithfulness_result": self.faithfulness_result.to_dict(),
            "validation_trace": self.validation_trace,
            "failure_reasons": self.failure_reasons,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        f_res = FaithfulnessResult.from_dict(data["faithfulness_result"])
        return cls(
            is_valid=data["is_valid"],
            citation_status=data["citation_status"],
            decision_consistent=data["decision_consistent"],
            severity_consistent=data["severity_consistent"],
            numeric_consistent=data.get("numeric_consistent", True),
            citation_coverage=float(data.get("citation_coverage", 0.0)),
            citation_precision=float(data.get("citation_precision", 0.0)),
            faithfulness_result=f_res,
            validation_trace=data.get("validation_trace", []),
            failure_reasons=data.get("failure_reasons", []),
        )


@dataclass
class ExplanationResult:
    """Structured, reproducible outcome of Phase 9 explanation orchestration."""
    explanation_id: str
    dataset: str
    split: str
    window_id: str
    incident_decision: str  # MUST preserve Phase 8 decision exactly
    severity: str  # MUST preserve Phase 8 severity exactly
    reasoning_confidence: float  # [0.0, 1.0] from Phase 8
    summary: str
    explanation: str
    claims: List[ExplanationClaim]
    citations: List[ExplanationCitation]
    uncertainties: List[str]
    recommended_action: Optional[str]
    provenance_status: str  # 'VERIFIED', 'INVALID', 'UNAVAILABLE'
    citation_validation_status: str  # 'VALID', 'INVALID'
    faithfulness_status: str  # One of FaithfulnessStatus
    explanation_status: str  # One of ExplanationStatus
    abstained: bool
    abstention_reason: Optional[str]
    model_name: str
    prompt_version: str
    explanation_engine_version: str
    input_artifact_hashes: Dict[str, str]
    configuration_hash: str
    validation_trace: List[Dict[str, Any]]
    usage_metadata: Optional[LLMUsageMetadata] = None
    created_timestamp: Optional[str] = None

    def to_dict(self, include_runtime: bool = True) -> Dict[str, Any]:
        """Convert explanation result to serializable dictionary.
        
        Args:
            include_runtime: If False, omits volatile fields (usage_metadata, created_timestamp)
                             for deterministic hashing and bitwise reproducibility.
        """
        data: Dict[str, Any] = {
            "explanation_id": self.explanation_id,
            "dataset": self.dataset,
            "split": self.split,
            "window_id": self.window_id,
            "incident_decision": self.incident_decision,
            "severity": self.severity,
            "reasoning_confidence": round(self.reasoning_confidence, 4),
            "summary": self.summary,
            "explanation": self.explanation,
            "claims": [c.to_dict() for c in self.claims],
            "citations": [c.to_dict() for c in self.citations],
            "uncertainties": list(self.uncertainties),
            "recommended_action": self.recommended_action,
            "provenance_status": self.provenance_status,
            "citation_validation_status": self.citation_validation_status,
            "faithfulness_status": self.faithfulness_status,
            "explanation_status": self.explanation_status,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
            "explanation_engine_version": self.explanation_engine_version,
            "input_artifact_hashes": self.input_artifact_hashes,
            "configuration_hash": self.configuration_hash,
            "validation_trace": self.validation_trace,
        }
        if include_runtime:
            data["usage_metadata"] = self.usage_metadata.to_dict() if self.usage_metadata else None
            data["created_timestamp"] = self.created_timestamp
        return data

    def compute_content_hash(self) -> str:
        """Compute deterministic SHA-256 fingerprint over content fields only."""
        canonical_dict = self.to_dict(include_runtime=False)
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplanationResult":
        claims = [ExplanationClaim.from_dict(c) for c in data.get("claims", [])]
        citations = [ExplanationCitation.from_dict(c) for c in data.get("citations", [])]
        usage = LLMUsageMetadata.from_dict(data["usage_metadata"]) if data.get("usage_metadata") else None
        return cls(
            explanation_id=data["explanation_id"],
            dataset=data["dataset"],
            split=data["split"],
            window_id=data["window_id"],
            incident_decision=data["incident_decision"],
            severity=data["severity"],
            reasoning_confidence=float(data["reasoning_confidence"]),
            summary=data["summary"],
            explanation=data["explanation"],
            claims=claims,
            citations=citations,
            uncertainties=list(data.get("uncertainties", [])),
            recommended_action=data.get("recommended_action"),
            provenance_status=data["provenance_status"],
            citation_validation_status=data["citation_validation_status"],
            faithfulness_status=data["faithfulness_status"],
            explanation_status=data["explanation_status"],
            abstained=data.get("abstained", False),
            abstention_reason=data.get("abstention_reason"),
            model_name=data["model_name"],
            prompt_version=data["prompt_version"],
            explanation_engine_version=data["explanation_engine_version"],
            input_artifact_hashes=data.get("input_artifact_hashes", {}),
            configuration_hash=data["configuration_hash"],
            validation_trace=data.get("validation_trace", []),
            usage_metadata=usage,
            created_timestamp=data.get("created_timestamp"),
        )
