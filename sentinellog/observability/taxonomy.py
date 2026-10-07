"""Event names and reliability error categories for SentinelLog Observability."""

from enum import Enum


class ObservabilityEvent(str, Enum):
    """Stable event taxonomy for SentinelLog structured logging and tracing."""

    APPLICATION_STARTED = "application_started"
    APPLICATION_SHUTDOWN = "application_shutdown"

    REQUEST_STARTED = "request_started"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_REJECTED = "request_rejected"

    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"

    INGESTION_STARTED = "ingestion_started"
    INGESTION_COMPLETED = "ingestion_completed"
    INGESTION_FAILED = "ingestion_failed"

    SCORING_STARTED = "scoring_started"
    SCORING_COMPLETED = "scoring_completed"
    SCORING_FAILED = "scoring_failed"

    GATE_AUTO_CLEAR = "gate_auto_clear"
    GATE_ESCALATE = "gate_escalate"

    RETRIEVAL_STARTED = "retrieval_started"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    RETRIEVAL_FAILED = "retrieval_failed"

    RERANKING_STARTED = "reranking_started"
    RERANKING_COMPLETED = "reranking_completed"
    RERANKING_FAILED = "reranking_failed"

    PROVENANCE_STARTED = "provenance_started"
    PROVENANCE_VERIFIED = "provenance_verified"
    PROVENANCE_REJECTED = "provenance_rejected"

    REASONING_STARTED = "reasoning_started"
    REASONING_COMPLETED = "reasoning_completed"
    REASONING_FAILED = "reasoning_failed"

    EXPLANATION_STARTED = "explanation_started"
    EXPLANATION_COMPLETED = "explanation_completed"
    EXPLANATION_FAILED = "explanation_failed"

    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_ERROR = "provider_error"

    VALIDATION_FAILED = "validation_failed"

    HEALTH_CHECK = "health_check"
    READINESS_FAILED = "readiness_failed"


class ReliabilityErrorCategory(str, Enum):
    """Normalized taxonomy of operational errors."""

    CLIENT_ERROR = "CLIENT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    PROVENANCE_ERROR = "PROVENANCE_ERROR"
    REASONING_ERROR = "REASONING_ERROR"
    EXPLANATION_ERROR = "EXPLANATION_ERROR"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
