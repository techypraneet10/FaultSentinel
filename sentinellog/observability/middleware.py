"""ASGI middleware for request correlation, structured access logging, tracing, and metrics."""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sentinellog.observability.config import get_observability_config
from sentinellog.observability.logging import (
    emit_event,
    set_current_request_id,
    set_current_trace_context,
)
from sentinellog.observability.metrics import get_metrics_registry
from sentinellog.observability.taxonomy import ObservabilityEvent
from sentinellog.observability.tracing import get_tracer

logger = logging.getLogger("sentinellog.serving.access")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Integrates request correlation, structured access events, tracing, and metric collection."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Request correlation: preserve X-Request-ID or generate new UUID4
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and len(incoming_id) <= 128 and incoming_id.replace("-", "").isalnum():
            request_id = incoming_id
        else:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        set_current_request_id(request_id)

        cfg = get_observability_config()
        registry = get_metrics_registry()
        tracer = get_tracer()

        endpoint = request.url.path
        # Sanitize endpoint for metric label (prevent high cardinality on dynamic paths)
        metric_endpoint = endpoint if endpoint in ("/api/v1/analyze", "/health/live", "/health/ready", "/health/observability", "/api/v1/diagnostics", "/metrics") else "other"

        start_time = time.perf_counter()

        # 2. Start root request span
        span = tracer.start_span(
            name=f"HTTP {request.method} {metric_endpoint}",
            attributes={
                "http.method": request.method,
                "http.target": endpoint,
            },
        )
        set_current_trace_context(span.trace_id, span.span_id)

        emit_event(
            logger,
            logging.DEBUG,
            ObservabilityEvent.REQUEST_STARTED.value,
            message=f"Started handling {request.method} {endpoint}",
            endpoint=metric_endpoint,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            span.record_exception(exc)
            span.end()
            tracer.record_span(span)

            # Record failure metrics
            try:
                registry.get_counter("request_count").inc(1.0, endpoint=metric_endpoint, status="failure")
                registry.get_counter("request_errors").inc(1.0, endpoint=metric_endpoint, status="failure")
                registry.get_counter("http_requests_by_family").inc(1.0, http_status_family="5xx")
                registry.get_histogram("request_latency").observe(duration_ms, endpoint=metric_endpoint)
            except Exception:
                pass

            emit_event(
                logger,
                logging.ERROR,
                ObservabilityEvent.REQUEST_REJECTED.value,
                message=f"Request failed with unhandled exception: {str(exc)}",
                endpoint=metric_endpoint,
                duration_ms=duration_ms,
                status="failure",
                error_code="INTERNAL_ERROR",
            )
            set_current_request_id(None)
            set_current_trace_context(None, None)
            raise exc

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id

        # Determine HTTP status family (2xx, 4xx, 5xx)
        status_code = response.status_code
        status_family = f"{status_code // 100}xx"
        req_status = "success" if status_code < 400 else "failure"

        span.set_attribute("http.status_code", status_code)
        span.set_status("OK" if status_code < 400 else "ERROR")
        span.end()
        try:
            tracer.record_span(span)
        except Exception:
            pass

        # Record metrics safely (non-fatal)
        try:
            registry.get_counter("request_count").inc(1.0, endpoint=metric_endpoint, status=req_status)
            if status_code >= 400:
                registry.get_counter("request_errors").inc(1.0, endpoint=metric_endpoint, status=req_status)
            registry.get_counter("http_requests_by_family").inc(1.0, http_status_family=status_family)
            registry.get_histogram("request_latency").observe(duration_ms, endpoint=metric_endpoint)
        except Exception:
            pass

        # Structured access log record
        log_level = logging.INFO if status_code < 500 else logging.ERROR
        emit_event(
            logger,
            log_level,
            ObservabilityEvent.REQUEST_COMPLETED.value,
            message=f"{request.method} {endpoint} {status_code} in {duration_ms}ms",
            endpoint=metric_endpoint,
            duration_ms=duration_ms,
            status=req_status,
        )

        set_current_request_id(None)
        set_current_trace_context(None, None)
        return response
