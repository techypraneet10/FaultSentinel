"""In-memory OpenTelemetry-compatible tracing with bounded memory buffer and context propagation."""

import random
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from sentinellog.observability.config import get_observability_config
from sentinellog.observability.logging import (
    get_current_request_id,
    set_current_trace_context,
)
from sentinellog.observability.redaction import redact_data


class Span:
    """Represents a discrete execution span within an operation trace."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        request_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.request_id = request_id or get_current_request_id()
        self.attributes: Dict[str, Any] = redact_data(attributes or {})
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "UNSET"  # OK, ERROR, UNSET
        self.error_message: Optional[str] = None
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single safe attribute on the span."""
        try:
            self.attributes[key] = redact_data(value)
        except Exception:
            pass

    def set_status(self, status: str, description: Optional[str] = None) -> None:
        """Set span status ('OK' or 'ERROR') and optional description."""
        self.status = status
        if description:
            self.error_message = str(description)

    def record_exception(self, exception: Exception) -> None:
        """Record an exception cleanly without leaking raw internal state."""
        self.status = "ERROR"
        self.error_message = f"{type(exception).__name__}: {str(exception)}"
        self.events.append({
            "name": "exception",
            "time": time.time(),
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
        })

    def end(self) -> None:
        """Mark span completion and calculate duration."""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
            if self.status == "UNSET":
                self.status = "OK"

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary format."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "request_id": self.request_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "attributes": self.attributes,
            "error_message": self.error_message,
        }


# Context tracking for active span
_ACTIVE_SPAN: ContextVar[Optional[Span]] = ContextVar("active_span", default=None)


class Tracer:
    """Manages span lifecycles, sampling, and in-memory bounded storage."""

    def __init__(self):
        self._spans_buffer: List[Dict[str, Any]] = []

    def start_span(
        self,
        name: str,
        parent: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span, respecting sampling configuration."""
        cfg = get_observability_config()
        if not cfg.tracing.enabled:
            # Return dummy span if tracing disabled
            return Span(name=name, trace_id="0", span_id="0")

        # Sampling check
        sample_rate = max(0.0, min(1.0, cfg.tracing.sample_rate))
        if sample_rate < 1.0 and random.random() > sample_rate:
            return Span(name=name, trace_id="0", span_id="0")

        parent_span = parent or _ACTIVE_SPAN.get()
        if parent_span and parent_span.trace_id != "0":
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_span_id = None

        span_id = uuid.uuid4().hex[:16]
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )
        return span

    def record_span(self, span: Span) -> None:
        """Buffer finished span safely within max_buffer_size limit."""
        if span.trace_id == "0":
            return
        cfg = get_observability_config()
        max_size = cfg.tracing.max_buffer_size
        if len(self._spans_buffer) >= max_size:
            # Evict oldest entry (FIFO) to keep buffer bounded
            self._spans_buffer.pop(0)
        self._spans_buffer.append(span.to_dict())

    def get_spans(self) -> List[Dict[str, Any]]:
        """Return a copy of buffered spans."""
        return list(self._spans_buffer)

    def clear(self) -> None:
        """Clear span buffer."""
        self._spans_buffer.clear()


_GLOBAL_TRACER: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Retrieve global Tracer instance."""
    global _GLOBAL_TRACER
    if _GLOBAL_TRACER is None:
        _GLOBAL_TRACER = Tracer()
    return _GLOBAL_TRACER


class trace_span:
    """Context manager for tracing execution blocks cleanly."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes
        self.span: Optional[Span] = None
        self._token = None

    def __enter__(self) -> Span:
        tracer = get_tracer()
        self.span = tracer.start_span(self.name, attributes=self.attributes)
        self._token = _ACTIVE_SPAN.set(self.span)
        set_current_trace_context(self.span.trace_id, self.span.span_id)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if self.span:
                if exc_type is not None and exc_val is not None:
                    self.span.record_exception(exc_val)
                self.span.end()
                try:
                    get_tracer().record_span(self.span)
                except Exception:
                    # Non-fatal telemetry: tracing export failure must never crash application
                    pass
        except Exception:
            pass
        finally:
            if self._token:
                _ACTIVE_SPAN.reset(self._token)
            # Restore parent trace context if any
            parent = _ACTIVE_SPAN.get()
            if parent:
                set_current_trace_context(parent.trace_id, parent.span_id)
            else:
                set_current_trace_context(None, None)
