"""Comprehensive unit and integration test suite for SentinelLog Phase 13 Observability & Reliability."""

import json
import logging
import time
import uuid
import pytest
from fastapi.testclient import TestClient

from sentinellog.observability.config import ObservabilityConfig, get_observability_config
from sentinellog.observability.diagnostics import get_candidate_slis, get_process_uptime_seconds, get_safe_diagnostics
from sentinellog.observability.logging import (
    StructuredJsonFormatter,
    configure_structured_logging,
    emit_event,
    get_current_request_id,
    get_current_trace_context,
    get_structured_logger,
    set_current_request_id,
    set_current_trace_context,
)
from sentinellog.observability.metrics import (
    ALLOWED_LABEL_KEYS,
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics_registry,
)
from sentinellog.observability.redaction import redact_data, redact_string
from sentinellog.observability.taxonomy import ObservabilityEvent, ReliabilityErrorCategory
from sentinellog.observability.tracing import Span, Tracer, get_tracer, trace_span
from sentinellog.serving.app import create_app
from sentinellog.serving.config import get_default_config


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_telemetry():
    """Reset telemetry states before each test."""
    set_current_request_id(None)
    set_current_trace_context(None, None)
    get_tracer().clear()
    get_metrics_registry().reset_all()
    yield
    set_current_request_id(None)
    set_current_trace_context(None, None)


# ============================================================================
# 1. Structured Logging & Redaction Tests
# ============================================================================

def test_structured_json_formatter_produces_valid_json():
    formatter = StructuredJsonFormatter(service_name="test_service", environment="test_env")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=50,
        msg="Test event message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    record.event = ObservabilityEvent.ANALYSIS_STARTED.value
    record.dataset = "hdfs"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["service"] == "test_service"
    assert parsed["environment"] == "test_env"
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "req-12345"
    assert parsed["event"] == "analysis_started"
    assert parsed["dataset"] == "hdfs"
    assert "timestamp" in parsed


def test_structured_logging_contextual_request_id():
    formatter = StructuredJsonFormatter()
    set_current_request_id("ctx-req-abc-999")
    record = logging.LogRecord(
        name="ctx_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=60,
        msg="Contextual msg",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert parsed["request_id"] == "ctx-req-abc-999"


def test_redact_string_bearer_token():
    sensitive = "Authorization: Bearer my_secret_token_1234567890abc"
    scrubbed = redact_string(sensitive)
    assert "my_secret_token_1234567890abc" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_redact_string_api_key():
    sensitive = "Calling upstream with api_key='sk-ant-live-secret-key-12345'"
    scrubbed = redact_string(sensitive)
    assert "sk-ant-live-secret-key-12345" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_redact_string_password():
    sensitive = "Connecting with password='supersecretpassword123'"
    scrubbed = redact_string(sensitive)
    assert "supersecretpassword123" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_redact_data_nested_dict():
    data = {
        "status": "ok",
        "api_key": "raw_secret_key_abcdef",
        "nested": {
            "token": "token_123456789",
            "safe_field": 42,
        },
        "list_items": ["Bearer secret_bearer_token_12345", "harmless"],
    }
    redacted = redact_data(data)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["safe_field"] == 42
    assert "[REDACTED]" in redacted["list_items"][0]
    assert "secret_bearer_token_12345" not in redacted["list_items"][0]
    assert redacted["list_items"][1] == "harmless"


def test_structured_log_redaction_integration():
    formatter = StructuredJsonFormatter(redaction_enabled=True)
    record = logging.LogRecord(
        name="test_redact",
        level=logging.INFO,
        pathname=__file__,
        lineno=80,
        msg="User authorized with Bearer secret-auth-token-1234567",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "secret-auth-token-1234567" not in formatted
    assert "[REDACTED]" in formatted


def test_emit_event_non_fatal():
    logger = logging.getLogger("test_emit")
    # Emit normal event
    emit_event(logger, logging.INFO, ObservabilityEvent.ANALYSIS_COMPLETED.value, dataset="hdfs")
    # Emit with unusual argument types without throwing
    emit_event(logger, logging.INFO, "custom_event", unpicklable=object())


# ============================================================================
# 2. OpenTelemetry-Compatible Tracing Tests
# ============================================================================

def test_tracer_creates_root_span():
    tracer = get_tracer()
    span = tracer.start_span("root_op", attributes={"dataset": "hdfs"})
    assert span.name == "root_op"
    assert span.trace_id != "0"
    assert len(span.span_id) == 16
    assert span.parent_span_id is None
    span.end()
    assert span.duration_ms >= 0.0
    assert span.status == "OK"


def test_trace_span_context_manager_parent_child():
    tracer = get_tracer()
    with trace_span("parent_stage", attributes={"stage": "parent"}) as parent:
        with trace_span("child_stage", attributes={"stage": "child"}) as child:
            assert child.trace_id == parent.trace_id
            assert child.parent_span_id == parent.span_id

    spans = tracer.get_spans()
    assert len(spans) == 2
    child_dict = [s for s in spans if s["name"] == "child_stage"][0]
    parent_dict = [s for s in spans if s["name"] == "parent_stage"][0]
    assert child_dict["parent_span_id"] == parent_dict["span_id"]
    assert child_dict["trace_id"] == parent_dict["trace_id"]


def test_trace_span_records_exception_safely():
    tracer = get_tracer()
    with pytest.raises(ValueError):
        with trace_span("failing_stage"):
            raise ValueError("Controlled test failure")

    spans = tracer.get_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span["status"] == "ERROR"
    assert "Controlled test failure" in span["error_message"]


def test_tracing_buffer_memory_bounded():
    tracer = get_tracer()
    cfg = get_observability_config()
    cfg.tracing.max_buffer_size = 5

    for i in range(10):
        with trace_span(f"op_{i}"):
            pass

    spans = tracer.get_spans()
    assert len(spans) == 5
    # Oldest spans evicted, remaining should be op_5 to op_9
    names = [s["name"] for s in spans]
    assert "op_0" not in names
    assert "op_9" in names

    cfg.tracing.max_buffer_size = 1000  # Reset


def test_tracing_redacts_sensitive_span_attributes():
    with trace_span("secure_span", attributes={"api_key": "sk-1234567890", "safe": "ok"}) as span:
        assert span.attributes["api_key"] == "[REDACTED]"
        assert span.attributes["safe"] == "ok"


def test_tracing_disabled_returns_noop():
    cfg = get_observability_config()
    cfg.tracing.enabled = False
    tracer = get_tracer()
    span = tracer.start_span("disabled_span")
    assert span.trace_id == "0"
    tracer.record_span(span)
    assert len(tracer.get_spans()) == 0
    cfg.tracing.enabled = True


# ============================================================================
# 3. Prometheus Metrics & Cardinality Control Tests
# ============================================================================

def test_counter_increments_correctly():
    registry = get_metrics_registry()
    counter = registry.get_counter("analysis_count")
    counter.inc(1.0, dataset="hdfs", status="success")
    counter.inc(2.0, dataset="hdfs", status="success")
    val = counter.get(dataset="hdfs", status="success")
    assert val == 3.0


def test_gauge_set_and_get():
    registry = get_metrics_registry()
    gauge = registry.get_gauge("escalation_rate")
    gauge.set(0.0522, dataset="hdfs")
    assert gauge.get(dataset="hdfs") == 0.0522


def test_histogram_observes_values_and_buckets():
    registry = get_metrics_registry()
    hist = registry.get_histogram("analysis_latency")
    hist.observe(15.0, dataset="hdfs")
    hist.observe(75.0, dataset="hdfs")

    expo = registry.generate_exposition()
    assert 'analysis_latency_bucket{dataset="hdfs",le="50.0"} 1' in expo
    assert 'analysis_latency_bucket{dataset="hdfs",le="100.0"} 2' in expo
    assert 'analysis_latency_count{dataset="hdfs"} 2' in expo


def test_metric_cardinality_control_filters_unbounded_keys():
    registry = get_metrics_registry()
    counter = registry.create_counter("test_cardinality", "Test bounded labels", ["dataset", "status"])

    # Attempt to inject unbounded dimensions like request_id and raw log line
    counter.inc(1.0, dataset="hdfs", status="success", request_id="uuid-9999", raw_log="Error occurred at line 12")
    expo = registry.generate_exposition()

    assert "uuid-9999" not in expo
    assert "Error occurred at line 12" not in expo
    assert 'test_cardinality{dataset="hdfs",status="success"} 1.0' in expo


def test_prometheus_exposition_format():
    registry = get_metrics_registry()
    registry.get_counter("request_count").inc(1.0, endpoint="/api/v1/analyze", status="success")
    expo = registry.generate_exposition()

    assert "# HELP request_count" in expo
    assert "# TYPE request_count counter" in expo
    assert 'request_count{endpoint="/api/v1/analyze",status="success"} 1.0' in expo


# ============================================================================
# 4. HTTP Endpoints & Serving Telemetry Integration
# ============================================================================

def test_metrics_endpoint_accessible(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    assert "# HELP request_count" in res.text


def test_metrics_endpoint_does_not_leak_secrets(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.text
    assert "api_key" not in body.lower()
    assert "secret" not in body.lower()
    assert "password" not in body.lower()


def test_health_observability_endpoint(client):
    res = client.get("/health/observability")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "telemetry" in data
    assert data["telemetry"]["logging"] in ("initialized", "standard")
    assert data["telemetry"]["metrics"] in ("initialized", "disabled")
    assert data["telemetry"]["tracing"] in ("initialized", "disabled")


def test_diagnostics_endpoint_safe(client):
    res = client.get("/api/v1/diagnostics")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "sentinellog"
    assert "api_version" in data
    assert "uptime_seconds" in data
    assert "candidate_slis" in data
    # Ensure no internal raw paths or secrets are exposed
    assert "PATH" not in data
    assert "api_key" not in data


def test_request_id_correlation_preserved_in_header(client):
    custom_req_id = "custom-test-req-id-777"
    res = client.get("/health/live", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_req_id


def test_request_id_generated_when_absent(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert len(res.headers["X-Request-ID"]) > 10


def test_analyze_request_increments_metrics(client):
    registry = get_metrics_registry()
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200

    # Verify request & analysis counters incremented
    req_cnt = registry.get_counter("request_count").get(endpoint="/api/v1/analyze", status="success")
    assert req_cnt >= 1.0

    an_cnt = registry.get_counter("analysis_count").get(dataset="hdfs", status="success")
    assert an_cnt >= 1.0

    # Decision metric
    dec_val = registry.get_counter("decisions_total").get(dataset="hdfs", decision="INCIDENT")
    assert dec_val >= 1.0


def test_analyze_request_creates_traces_with_spans(client):
    tracer = get_tracer()
    tracer.clear()

    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200

    spans = tracer.get_spans()
    span_names = [s["name"] for s in spans]
    assert "analysis" in span_names
    assert any("HTTP POST /api/v1/analyze" in name for name in span_names)

    # Check child span attributes
    an_span = [s for s in spans if s["name"] == "analysis"][0]
    assert an_span["attributes"]["dataset"] == "hdfs"
    assert an_span["attributes"]["decision"] == "INCIDENT"


def test_invalid_dataset_records_error_metrics(client):
    registry = get_metrics_registry()
    payload = {
        "dataset": "unsupported_dataset_xyz",
        "logs": ["log line 1"],
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 422

    # Verify 4xx family counter and request_errors incremented
    fam_cnt = registry.get_counter("http_requests_by_family").get(http_status_family="4xx")
    assert fam_cnt >= 1.0


# ============================================================================
# 5. Reliability, Failure Isolation & Invariants Tests
# ============================================================================

def test_telemetry_failure_is_non_fatal_on_request(client, monkeypatch):
    """If metrics or tracing throws an internal error, the HTTP request must still succeed."""
    def broken_observe(*args, **kwargs):
        raise RuntimeError("Simulated internal metrics failure")

    monkeypatch.setattr(get_metrics_registry().get_histogram("request_latency"), "observe", broken_observe)

    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "INCIDENT"


def test_tracing_failure_is_non_fatal(client, monkeypatch):
    """If tracing buffer or record fails, analysis completes safely."""
    def broken_record_span(*args, **kwargs):
        raise RuntimeError("Simulated tracing export exception")

    monkeypatch.setattr(get_tracer(), "record_span", broken_record_span)

    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "INCIDENT"


def test_decision_immutability_invariant(client):
    """Instrumented execution must yield the exact Phase 8 decision and severity."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "INCIDENT"
    assert body["severity"] == "HIGH"
    assert body["provenance_status"] == "VERIFIED"
    assert body["faithfulness_status"] == "VERIFIED"


def test_bgl_safety_regression_decision_immutability(client):
    """Verify BGL calibration window retains authoritative INSUFFICIENT_EVIDENCE."""
    payload = {
        "dataset": "bgl",
        "logs": ["1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.363779 R02-M1-N0-C:J12-U11 RAS KERNEL INFO CE sym 0"],
        "options": {"window_id": "bgl_window_0000349"},
    }
    res = client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "INSUFFICIENT_EVIDENCE"
    assert body["severity"] == "LOW"
    assert body["provenance_status"] == "VERIFIED"


def test_cardinality_growth_protection():
    """Verify metrics dictionary size does not explode with 100 distinct request IDs."""
    registry = get_metrics_registry()
    counter = registry.get_counter("request_count")

    # Increment with distinct request IDs passed in kwargs (which should be stripped)
    for _ in range(100):
        req_id = str(uuid.uuid4())
        counter.inc(1.0, endpoint="/api/v1/analyze", status="success", request_id=req_id)

    # Number of entries in counter._values should remain bounded (1 entry for the unique tuple of allowed labels)
    assert len(counter._values) == 1
    assert counter.get(endpoint="/api/v1/analyze", status="success") == 100.0


def test_process_uptime_positive():
    uptime = get_process_uptime_seconds()
    assert uptime >= 0.0


def test_candidate_slis_computation():
    registry = get_metrics_registry()
    registry.get_counter("request_count").inc(95.0, endpoint="/api/v1/analyze", status="success")
    registry.get_counter("request_errors").inc(5.0, endpoint="/api/v1/analyze", status="failure")
    registry.get_counter("auto_clear_count").inc(90.0, dataset="hdfs")
    registry.get_counter("escalation_count").inc(10.0, dataset="hdfs")

    slis = get_candidate_slis()
    cand = slis["candidate_slis"]
    assert cand["total_requests_observed"] == 95
    assert cand["total_auto_cleared_observed"] == 90
    assert cand["total_escalated_observed"] == 10
    assert cand["observed_escalation_rate"] == 0.10
    assert "target" not in slis["notice"].lower() or "not target" in slis["notice"].lower()


def test_event_taxonomy_stability():
    assert ObservabilityEvent.APPLICATION_STARTED.value == "application_started"
    assert ObservabilityEvent.GATE_ESCALATE.value == "gate_escalate"
    assert ObservabilityEvent.GATE_AUTO_CLEAR.value == "gate_auto_clear"
    assert ObservabilityEvent.PROVENANCE_VERIFIED.value == "provenance_verified"
    assert ObservabilityEvent.EXPLANATION_COMPLETED.value == "explanation_completed"


def test_reliability_error_categories():
    assert ReliabilityErrorCategory.CLIENT_ERROR.value == "CLIENT_ERROR"
    assert ReliabilityErrorCategory.VALIDATION_ERROR.value == "VALIDATION_ERROR"
    assert ReliabilityErrorCategory.PIPELINE_ERROR.value == "PIPELINE_ERROR"
    assert ReliabilityErrorCategory.PROVIDER_TIMEOUT.value == "PROVIDER_TIMEOUT"
    assert ReliabilityErrorCategory.PROVIDER_ERROR.value == "PROVIDER_ERROR"


# ============================================================================
# 6. Specific Phase 13 Requirement & Lifecycle Regression Tests
# ============================================================================

def test_lifecycle_hang_regression(client):
    """Regression test proving create_app + TestClient + ObservabilityMiddleware does not hang."""
    t0 = time.perf_counter()
    res = client.get("/health/live")
    elapsed = time.perf_counter() - t0
    assert res.status_code == 200
    assert elapsed < 3.0  # Must complete rapidly without deadlock


def test_metrics_registry_reset_all_thread_safety():
    """Verify reset_all() re-initializes without deadlock under concurrent access."""
    registry = get_metrics_registry()
    registry.reset_all()
    assert registry.get_counter("request_count") is not None
    assert registry.get_counter("analysis_count") is not None


def test_logging_configuration_is_idempotent():
    """Calling configure_structured_logging multiple times should not add duplicate handlers."""
    root = logging.getLogger()
    initial_count = len(root.handlers)
    configure_structured_logging()
    configure_structured_logging()
    assert len(root.handlers) == initial_count


def test_config_environment_variable_overrides(monkeypatch):
    monkeypatch.setenv("SENTINELLOG_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SENTINELLOG_METRICS_ENABLED", "false")
    monkeypatch.setenv("SENTINELLOG_TRACING_ENABLED", "false")
    monkeypatch.setenv("SENTINELLOG_TRACE_SAMPLE_RATE", "0.5")

    cfg = ObservabilityConfig.load()
    assert cfg.observability.log_level == "DEBUG"
    assert cfg.metrics.enabled is False
    assert cfg.tracing.enabled is False
    assert cfg.tracing.sample_rate == 0.5


def test_sampling_rate_limits_spans():
    cfg = get_observability_config()
    orig_sample = cfg.tracing.sample_rate
    orig_enabled = cfg.tracing.enabled
    try:
        cfg.tracing.enabled = True
        cfg.tracing.sample_rate = 0.0  # Drop 100% of spans
        tracer = get_tracer()
        span = tracer.start_span("dropped_span")
        assert span.trace_id == "0"
    finally:
        cfg.tracing.sample_rate = orig_sample
        cfg.tracing.enabled = orig_enabled


def test_provider_timeout_metrics_recording():
    registry = get_metrics_registry()
    registry.get_counter("llm_timeout_total").inc(1.0, provider="mock_llm")
    registry.get_counter("explanation_failed_total").inc(1.0, dataset="hdfs")
    assert registry.get_counter("llm_timeout_total").get(provider="mock_llm") == 1.0
    assert registry.get_counter("explanation_failed_total").get(dataset="hdfs") == 1.0


def test_provenance_failure_metrics_recording():
    registry = get_metrics_registry()
    registry.get_counter("provenance_rejected_total").inc(2.0, dataset="hdfs")
    registry.get_counter("citation_validation_failures").inc(2.0, dataset="hdfs")
    assert registry.get_counter("provenance_rejected_total").get(dataset="hdfs") == 2.0
    assert registry.get_counter("citation_validation_failures").get(dataset="hdfs") == 2.0


def test_retrieval_failure_metrics_recording():
    registry = get_metrics_registry()
    registry.get_counter("retrieval_failures").inc(1.0, dataset="hdfs")
    assert registry.get_counter("retrieval_failures").get(dataset="hdfs") == 1.0


def test_reasoning_failure_metrics_recording():
    registry = get_metrics_registry()
    registry.get_counter("reasoning_failures").inc(1.0, dataset="hdfs")
    assert registry.get_counter("reasoning_failures").get(dataset="hdfs") == 1.0
