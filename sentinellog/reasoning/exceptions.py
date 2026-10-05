"""Exception taxonomy for Phase 8 Incident Reasoning Engine.

Ensures deterministic fail-closed behavior for:
- Invalid or missing provenance
- Label leakage attempts
- Test split access attempts
- Configuration errors
"""


class ReasoningError(Exception):
    """Base exception for all reasoning engine errors."""
    pass


class ProvenanceInvalidError(ReasoningError):
    """Raised when an evidence citation or bundle fails integrity or addressability verification."""
    pass


class InsufficientEvidenceError(ReasoningError):
    """Raised when evidence sufficiency cannot be evaluated or is critically missing."""
    pass


class LabelLeakageError(ReasoningError):
    """Raised when ground-truth anomaly labels are detected in reasoning inputs."""
    pass


class InvalidSplitError(ReasoningError):
    """Raised when non-permitted data partitions (especially TEST) are supplied to the engine."""
    pass


class ConfigurationError(ReasoningError):
    """Raised when reasoning configuration is missing or malformed."""
    pass
