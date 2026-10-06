"""Custom exceptions for SentinelLog Serving Layer."""

from typing import Any, Dict, Optional


class SentinelLogServingError(Exception):
    """Base exception for all serving layer errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InvalidRequestError(SentinelLogServingError):
    """Raised when client input fails application validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=400,
            details=details,
        )


class UnsupportedDatasetError(SentinelLogServingError):
    """Raised when requested dataset is not in supported list."""

    def __init__(self, dataset: str):
        super().__init__(
            message=f"Dataset '{dataset}' is unsupported. Supported datasets: ['hdfs', 'bgl'].",
            code="UNSUPPORTED_DATASET",
            status_code=422,
            details={"dataset": dataset, "supported": ["hdfs", "bgl"]},
        )


class PayloadTooLargeError(SentinelLogServingError):
    """Raised when request payload or log collection exceeds configured limits."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PAYLOAD_TOO_LARGE",
            status_code=413,
            details=details,
        )


class PipelineServingError(SentinelLogServingError):
    """Raised when an internal pipeline component encounters an unrecoverable failure."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PIPELINE_ERROR",
            status_code=500,
            details=details,
        )


class ProvenanceServingError(SentinelLogServingError):
    """Raised when evidence provenance integrity or verification fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PROVENANCE_ERROR",
            status_code=500,
            details=details,
        )


class ExplanationServingError(SentinelLogServingError):
    """Raised when explanation generation or verification fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EXPLANATION_ERROR",
            status_code=500,
            details=details,
        )


class ServiceUnavailableError(SentinelLogServingError):
    """Raised when a required service dependency is not available or unhealthy."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class LabelLeakageAttemptError(SentinelLogServingError):
    """Raised when request attempts to inject ground truth labels."""

    def __init__(self, message: str = "Label leakage attempt detected: ground truth fields are forbidden."):
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=422,
            details={"reason": "forbidden_fields"},
        )
