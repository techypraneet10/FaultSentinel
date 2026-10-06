"""Exceptions for Phase 9 LLM Explanation & Orchestration Layer."""


class ExplanationError(Exception):
    """Base exception for all explanation layer errors."""
    pass


class ExplanationValidationError(ExplanationError):
    """Raised when generated explanation fails structural or semantic validation."""
    pass


class DecisionImmutabilityError(ExplanationValidationError):
    """Raised when generated explanation attempts to alter Phase 8 deterministic decision."""
    pass


class SeverityImmutabilityError(ExplanationValidationError):
    """Raised when generated explanation attempts to alter Phase 8 deterministic severity."""
    pass


class CitationValidationError(ExplanationValidationError):
    """Raised when citation validation fails (e.g. fabricated or nonexistent citation IDs)."""
    pass


class ClaimValidationError(ExplanationValidationError):
    """Raised when factual claim validation fails or violates claim taxonomy."""
    pass


class FaithfulnessCheckError(ExplanationValidationError):
    """Raised when explanation fails the deterministic faithfulness / grounding check."""
    pass


class ProviderError(ExplanationError):
    """Raised when LLM provider experiences an unrecoverable runtime error."""
    pass


class ProviderTimeoutError(ProviderError):
    """Raised when LLM provider exceeds execution timeout."""
    pass


class LabelLeakageError(ExplanationError):
    """Raised when sensitive labels or ground truth enter the LLM context or explanation."""
    pass


class MalformedOutputError(ExplanationValidationError):
    """Raised when LLM output cannot be parsed into the required structured schema."""
    pass


class InvalidSplitError(ExplanationError):
    """Raised when an operation is attempted on an unauthorized split (e.g. test set)."""
    pass


class ConfigurationError(ExplanationError):
    """Raised when explanation engine configuration is missing, malformed, or invalid."""
    pass
