"""SentinelLog Phase 8: Deterministic Incident Reasoning Engine.

Transforms selective escalations, retrieved evidence, and verified provenance citations
into auditable, deterministic incident assessments without LLM text generation.
"""

from sentinellog.reasoning.aggregation import SignalAggregator
from sentinellog.reasoning.artifacts import save_reasoning_artifacts
from sentinellog.reasoning.classifier import IncidentClassifier
from sentinellog.reasoning.confidence import ReasoningConfidenceCalculator
from sentinellog.reasoning.engine import (
    IncidentReasoningEngine,
    compute_configuration_hash,
)
from sentinellog.reasoning.exceptions import (
    ConfigurationError,
    InsufficientEvidenceError,
    InvalidSplitError,
    LabelLeakageError,
    ProvenanceInvalidError,
    ReasoningError,
)
from sentinellog.reasoning.rules import RuleEngine
from sentinellog.reasoning.schemas import (
    ContributionType,
    EvidenceContribution,
    IncidentAssessment,
    IncidentDecision,
    IncidentRule,
    IncidentSeverity,
    IncidentSignal,
    ProvenanceStatus,
    ReasoningResult,
    ReasoningSummary,
    ReasoningTrace,
    SufficiencyStatus,
)
from sentinellog.reasoning.signals import SignalExtractor
from sentinellog.reasoning.validation import (
    validate_no_label_leakage,
    validate_provenance_gate,
    validate_reasoning_split,
)
from sentinellog.reasoning.version import ENGINE_VERSION, SCHEMA_VERSION

__all__ = [
    "IncidentDecision",
    "IncidentSeverity",
    "ContributionType",
    "SufficiencyStatus",
    "ProvenanceStatus",
    "IncidentSignal",
    "EvidenceContribution",
    "IncidentRule",
    "ReasoningTrace",
    "IncidentAssessment",
    "ReasoningResult",
    "ReasoningSummary",
    "IncidentReasoningEngine",
    "IncidentClassifier",
    "compute_configuration_hash",
    "SignalExtractor",
    "SignalAggregator",
    "RuleEngine",
    "ReasoningConfidenceCalculator",
    "save_reasoning_artifacts",
    "validate_no_label_leakage",
    "validate_provenance_gate",
    "validate_reasoning_split",
    "ReasoningError",
    "ProvenanceInvalidError",
    "InsufficientEvidenceError",
    "LabelLeakageError",
    "InvalidSplitError",
    "ConfigurationError",
    "ENGINE_VERSION",
    "SCHEMA_VERSION",
]
