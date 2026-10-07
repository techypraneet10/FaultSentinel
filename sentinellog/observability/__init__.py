"""SentinelLog Observability & Reliability package."""

from sentinellog.observability.config import ObservabilityConfig, get_observability_config
from sentinellog.observability.diagnostics import get_candidate_slis, get_safe_diagnostics
from sentinellog.observability.logging import (
    StructuredJsonFormatter,
    configure_structured_logging,
    emit_event,
    get_current_request_id,
    get_current_trace_context,
    get_structured_logger,
    set_current_request_id,
)
from sentinellog.observability.metrics import MetricsRegistry, get_metrics_registry
from sentinellog.observability.middleware import ObservabilityMiddleware
from sentinellog.observability.redaction import redact_data, redact_string
from sentinellog.observability.taxonomy import ObservabilityEvent, ReliabilityErrorCategory
from sentinellog.observability.tracing import Span, Tracer, get_tracer, trace_span

__all__ = [
    "ObservabilityConfig",
    "get_observability_config",
    "ObservabilityEvent",
    "ReliabilityErrorCategory",
    "StructuredJsonFormatter",
    "configure_structured_logging",
    "get_structured_logger",
    "emit_event",
    "set_current_request_id",
    "get_current_request_id",
    "get_current_trace_context",
    "redact_string",
    "redact_data",
    "Span",
    "Tracer",
    "get_tracer",
    "trace_span",
    "MetricsRegistry",
    "get_metrics_registry",
    "get_safe_diagnostics",
    "get_candidate_slis",
    "ObservabilityMiddleware",
]
