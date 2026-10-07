"""Structured JSON logging with request correlation and automatic redaction."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sentinellog.observability.config import get_observability_config
from sentinellog.observability.redaction import redact_data, redact_string

# Request correlation context variable
_CURRENT_REQUEST_ID: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)
_CURRENT_TRACE_ID: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_CURRENT_SPAN_ID: ContextVar[Optional[str]] = ContextVar("current_span_id", default=None)


def set_current_request_id(request_id: Optional[str]) -> None:
    """Set the contextual request ID for structured logging and correlation."""
    _CURRENT_REQUEST_ID.set(request_id)


def get_current_request_id() -> Optional[str]:
    """Get the contextual request ID."""
    return _CURRENT_REQUEST_ID.get()


def set_current_trace_context(trace_id: Optional[str], span_id: Optional[str]) -> None:
    """Set current trace and span ID for context propagation in logs."""
    _CURRENT_TRACE_ID.set(trace_id)
    _CURRENT_SPAN_ID.set(span_id)


def get_current_trace_context() -> tuple[Optional[str], Optional[str]]:
    """Return (trace_id, span_id)."""
    return _CURRENT_TRACE_ID.get(), _CURRENT_SPAN_ID.get()


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with standard fields and redaction."""

    def __init__(self, service_name: str = "sentinellog", environment: str = "development", redaction_enabled: bool = True):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.redaction_enabled = redaction_enabled

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        req_id = getattr(record, "request_id", None) or get_current_request_id()
        trace_id, span_id = get_current_trace_context()

        event = getattr(record, "event", None) or record.getMessage()
        msg_str = record.getMessage()

        payload: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "logger": record.name,
            "message": msg_str,
        }

        if req_id:
            payload["request_id"] = req_id
        if trace_id:
            payload["trace_id"] = trace_id
        if span_id:
            payload["span_id"] = span_id
        if getattr(record, "event", None):
            payload["event"] = record.event

        # Copy any additional structured attributes
        for key in ("endpoint", "duration_ms", "status", "dataset", "decision", "severity", "error_code"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val

        if record.exc_info and record.exc_text:
            payload["exception"] = record.exc_text
        elif record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if self.redaction_enabled:
            payload = redact_data(payload)

        try:
            return json.dumps(payload, default=str)
        except Exception:
            # Non-fatal logging formatting fallback
            return json.dumps({
                "timestamp": timestamp,
                "level": record.levelname,
                "service": self.service_name,
                "message": redact_string(str(record.msg)) if self.redaction_enabled else str(record.msg),
            })


_STRUCTURED_LOGGING_CONFIGURED = False


def configure_structured_logging() -> None:
    """Set up root logger formatting according to ObservabilityConfig."""
    global _STRUCTURED_LOGGING_CONFIGURED
    if _STRUCTURED_LOGGING_CONFIGURED:
        return

    cfg = get_observability_config()
    level_name = cfg.observability.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Check if a StructuredJsonFormatter is already attached
    has_structured_handler = any(
        isinstance(getattr(h, "formatter", None), StructuredJsonFormatter)
        for h in root_logger.handlers
    )

    if not has_structured_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        if cfg.observability.json_logging:
            formatter = StructuredJsonFormatter(
                service_name=cfg.observability.service_name,
                environment=cfg.observability.environment,
                redaction_enabled=cfg.observability.redaction_enabled,
            )
            handler.setFormatter(formatter)
        else:
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    _STRUCTURED_LOGGING_CONFIGURED = True


def get_structured_logger(name: str) -> logging.Logger:
    """Convenience helper to retrieve a named logger."""
    return logging.getLogger(name)


def emit_event(
    logger: logging.Logger,
    level: int,
    event: str,
    message: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Emit a structured event with bounded parameters safely."""
    try:
        extra_dict = {"event": event}
        extra_dict.update(kwargs)
        logger.log(level, message or event, extra=extra_dict)
    except Exception:
        # Non-fatal telemetry: logging failure must never crash application
        pass
