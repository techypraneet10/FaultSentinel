"""Comprehensive test suite for Phase 10: FastAPI Application & Serving Layer.

Covers:
1. Application factory, OpenAPI schema compliance, and API versioning.
2. Health probes (/health/live, /health/ready) and readiness failure states.
3. Request schema validation (empty logs, unsupported datasets, oversized limits, malformed payloads, forbidden keys).
4. Core analysis orchestration for HDFS and BGL.
5. Decision immutability and Phase 8 / Phase 9 preservation.
6. Error handling, centralized exception mapping, and structured error responses.
7. Security controls: request ID propagation, security headers, CORS, path traversal, and label leakage protection.
8. Regressions: Phase 7 citation integrity, Phase 8 decision distribution, and Phase 9 claim grounding.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from sentinellog.serving.app import create_app
from sentinellog.serving.config import ServingConfig
from sentinellog.serving.dependencies import get_pipeline_service
from sentinellog.serving.errors.exceptions import (
    InvalidRequestError,
    PipelineServingError,
    ProvenanceServingError,
    ServiceUnavailableError,
)
from sentinellog.serving.services.pipeline_service import PipelineService
from sentinellog.serving.version import API_VERSION, SERVING_VERSION


@pytest.fixture
def app_client():
    """Default test client with standard serving configuration."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)
    return TestClient(app)


# ============================================================================
# 1. APPLICATION & OPENAPI TESTS
# ============================================================================

def test_create_app_instance():
    """Verify application factory initializes with correct metadata."""
    app = create_app()
    assert app.title in ("SentinelLog Serving API", "FaultSentinel Serving API")
    assert app.version == SERVING_VERSION


def test_openapi_schema_endpoint(app_client):
    """Verify OpenAPI 3.x schema generation and required endpoints."""
    res = app_client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1" in paths
    assert "/api/v1/analyze" in paths


def test_docs_and_redoc_endpoints(app_client):
    """Verify interactive Swagger UI and ReDoc documentation routes."""
    res_docs = app_client.get("/docs")
    assert res_docs.status_code == 200
    res_redoc = app_client.get("/redoc")
    assert res_redoc.status_code == 200


def test_api_root_metadata(app_client):
    """Verify /api/v1 returns public service metadata without internal leaks."""
    res = app_client.get("/api/v1")
    assert res.status_code == 200
    data = res.json()
    assert data["service_name"] == "SentinelLog"
    assert data["api_version"] == API_VERSION
    assert data["app_version"] == SERVING_VERSION
    assert data["status"] == "operational"
    # Ensure no secrets or internal paths are returned
    assert "data_root" not in data
    assert "secret" not in data


def test_api_versioning_boundary(app_client):
    """Verify unversioned endpoints (outside health) return 404."""
    res = app_client.post("/analyze", json={"dataset": "hdfs", "logs": ["log"]})
    assert res.status_code == 404


# ============================================================================
# 2. HEALTH & READINESS PROBE TESTS
# ============================================================================

def test_health_live_probe(app_client):
    """Verify liveness probe returns 200 OK."""
    res = app_client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_ready_probe_success(app_client):
    """Verify readiness probe returns ready status when models are loaded."""
    res = app_client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["checks"]["pipeline"] == "ok"
    assert data["checks"]["configuration"] == "ok"


def test_health_ready_probe_unhealthy():
    """Verify readiness probe returns 503 Service Unavailable when pipeline not ready."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    mock_pipeline = MagicMock()
    mock_pipeline.is_ready.return_value = False
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    client = TestClient(app)
    res = client.get("/health/ready")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["pipeline"] == "not_ready"


def test_health_live_does_not_depend_on_pipeline():
    """Verify liveness remains 200 even if pipeline is not ready."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    mock_pipeline = MagicMock()
    mock_pipeline.is_ready.return_value = False
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    client = TestClient(app)
    res = client.get("/health/live")
    assert res.status_code == 200


def test_health_ready_structure(app_client):
    """Verify readiness payload adheres strictly to HealthReadyResponse schema."""
    res = app_client.get("/health/ready")
    assert "status" in res.json()
    assert "checks" in res.json()


# ============================================================================
# 3. REQUEST VALIDATION TESTS
# ============================================================================

def test_valid_request_format(app_client):
    """Verify valid analysis payload format accepted."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Test event"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200


def test_empty_logs_rejected(app_client):
    """Verify empty log sequence rejected with 422."""
    res = app_client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": []})
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_unsupported_dataset_rejected(app_client):
    """Verify unsupported dataset name rejected with 422 UNSUPPORTED_DATASET."""
    res = app_client.post("/api/v1/analyze", json={"dataset": "syslog", "logs": ["log line"]})
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "UNSUPPORTED_DATASET"


def test_oversized_log_records_rejected(app_client):
    """Verify payload exceeding 500 records rejected with 422."""
    oversized = ["log line"] * 501
    res = app_client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": oversized})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_REQUEST"


def test_oversized_log_line_length_rejected(app_client):
    """Verify individual log line exceeding 4096 characters rejected with 422."""
    long_line = "A" * 4097
    res = app_client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": [long_line]})
    assert res.status_code == 422
    assert "exceeds maximum allowed length" in res.json()["error"]["details"]["validation_errors"][0]["msg"]


def test_malformed_json_payload_rejected(app_client):
    """Verify non-JSON or malformed payload rejected."""
    res = app_client.post(
        "/api/v1/analyze",
        content="not a json payload",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


def test_unexpected_fields_rejected(app_client):
    """Verify extra/unknown input fields rejected due to extra='forbid'."""
    payload = {
        "dataset": "hdfs",
        "logs": ["event log"],
        "unexpected_field": "disallowed",
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_REQUEST"


def test_unexpected_options_fields_rejected(app_client):
    """Verify extra options fields rejected due to extra='forbid'."""
    payload = {
        "dataset": "hdfs",
        "logs": ["event log"],
        "options": {"unsupported_option": True},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 422


# ============================================================================
# 4. ANALYSIS & PIPELINE ORCHESTRATION TESTS
# ============================================================================

def test_successful_hdfs_analysis(app_client):
    """Verify complete HDFS triage analysis request returning structured response."""
    payload = {
        "dataset": "hdfs",
        "logs": [
            "081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450",
        ],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["dataset"] == "hdfs"
    assert data["decision"] == "INCIDENT"
    assert data["severity"] == "HIGH"
    assert data["confidence"] > 0.0
    assert len(data["claims"]) > 0
    assert len(data["citations"]) > 0
    assert data["explanation_status"] == "GENERATED"
    assert data["faithfulness_status"] == "VERIFIED"


def test_successful_bgl_analysis(app_client):
    """Verify complete BGL triage analysis preserving INSUFFICIENT_EVIDENCE."""
    payload = {
        "dataset": "bgl",
        "logs": [
            "1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.363779 R02-M1-N0-C:J12-U11 RAS KERNEL INFO CE sym 0",
        ],
        "options": {"window_id": "bgl_window_0000349"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["dataset"] == "bgl"
    assert data["decision"] == "INSUFFICIENT_EVIDENCE"
    assert data["severity"] == "LOW"
    assert len(data["citations"]) > 0


def test_session_id_automatic_lookup(app_client):
    """Verify HDFS block ID embedded in log automatically resolves calibration window."""
    payload = {
        "dataset": "hdfs",
        "logs": [
            "081109 203518 143 INFO dfs.DataNode: Serving block blk_-7628164677193243450 to /10.250.19.102:54106",
        ],
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "INCIDENT"


def test_default_calibration_fallback(app_client):
    """Verify unindexed log sequence falls back to default calibration window for dataset."""
    payload = {
        "dataset": "hdfs",
        "logs": ["Generic unindexed log event without block ID"],
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_citations_excluded_when_requested(app_client):
    """Verify citations omitted when include_citations=False."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {
            "window_id": "hdfs_session_blk_-7628164677193243450",
            "include_citations": False,
        },
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert len(res.json()["citations"]) == 0


def test_raw_excerpts_excluded_by_default(app_client):
    """Verify raw citation text is excluded by default for safe coordinate response."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    for cit in res.json()["citations"]:
        assert cit["citation_text"] is None


# ============================================================================
# 5. DECISION IMMUTABILITY & SAFETY REGRESSION TESTS
# ============================================================================

def test_bgl_safety_regression_insufficient_evidence(app_client):
    """Rule 51: BGL analysis must strictly preserve INSUFFICIENT_EVIDENCE."""
    payload = {
        "dataset": "bgl",
        "logs": ["1117838570 2005.06.03 RAS KERNEL INFO CE sym 0"],
        "options": {"window_id": "bgl_window_0000350"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "INSUFFICIENT_EVIDENCE"
    assert data["decision"] != "INCIDENT"


def test_hdfs_decision_preservation_incident(app_client):
    """Rule 52: HDFS INCIDENT window preserved strictly."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "INCIDENT"
    assert res.json()["severity"] == "HIGH"


def test_hdfs_decision_preservation_suspicious(app_client):
    """Rule 52: HDFS SUSPICIOUS window preserved strictly."""
    # Lookup first SUSPICIOUS window
    cfg = ServingConfig.load("configs/phase10.yaml")
    p_service = PipelineService(cfg)
    susp_win = None
    for win_id, (assess, _, _) in p_service._cached_windows["hdfs"].items():
        if assess.decision == "SUSPICIOUS":
            susp_win = win_id
            break

    assert susp_win is not None
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode test log"],
        "options": {"window_id": susp_win},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "SUSPICIOUS"


def test_decision_immutability_conflict_rejected():
    """Rule 13: Conflict between explanation decision and Phase 8 decision triggers 500 error."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    # Mock pipeline returning conflicting decision
    mock_pipeline = MagicMock()
    mock_assess = MagicMock()
    mock_assess.decision = "INCIDENT"
    mock_assess.severity = "HIGH"
    mock_exp = MagicMock()
    mock_exp.incident_decision = "NORMAL"  # CONFLICT
    mock_exp.severity = "HIGH"
    mock_pipeline.process_analysis.return_value = (mock_assess, None, mock_exp)

    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline
    client = TestClient(app)

    res = client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": ["log"]})
    assert res.status_code == 500
    assert "Decision immutability invariant violated" in res.json()["error"]["message"]


# ============================================================================
# 6. ERROR HANDLING & RESPONSE ENVELOPE TESTS
# ============================================================================

def test_pipeline_domain_error_mapping():
    """Verify internal PipelineServingError maps to 500 with structured envelope."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    mock_pipeline = MagicMock()
    mock_pipeline.process_analysis.side_effect = PipelineServingError("Simulated pipeline failure")
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    client = TestClient(app)
    res = client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": ["log"]})
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "PIPELINE_ERROR"
    assert "Simulated pipeline failure" in data["error"]["message"]
    assert "request_id" in data["error"]


def test_provenance_error_mapping():
    """Verify ProvenanceServingError maps to structured error envelope."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    mock_pipeline = MagicMock()
    mock_pipeline.process_analysis.side_effect = ProvenanceServingError("Dual-hash mismatch")
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    client = TestClient(app)
    res = client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": ["log"]})
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "PIPELINE_ERROR"


def test_unhandled_exception_hides_traceback():
    """Verify raw Python exceptions return 500 without leaking stack traces."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    app = create_app(config=cfg)

    mock_pipeline = MagicMock()
    mock_pipeline.process_analysis.side_effect = RuntimeError("Sensitive DB error /secret/db.key")
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    client = TestClient(app)
    res = client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": ["log"]})
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "PIPELINE_ERROR"
    # Verify sensitive path is not exposed in public message
    assert "/secret/db.key" not in data["error"]["message"]


def test_error_envelope_preserves_request_id(app_client):
    """Verify custom X-Request-ID preserved in error response envelope."""
    custom_id = "trace-err-test-999"
    res = app_client.post(
        "/api/v1/analyze",
        json={"dataset": "invalid_ds", "logs": ["log"]},
        headers={"X-Request-ID": custom_id},
    )
    assert res.status_code == 422
    assert res.headers.get("X-Request-ID") == custom_id
    assert res.json()["error"]["request_id"] == custom_id


# ============================================================================
# 7. SECURITY CONTROLS & HEADERS TESTS
# ============================================================================

def test_request_id_generated_automatically(app_client):
    """Verify unique UUID request ID generated when client provides none."""
    res = app_client.get("/health/live")
    assert res.status_code == 200
    req_id = res.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_request_id_propagated_from_client(app_client):
    """Verify client X-Request-ID header is propagated."""
    client_id = "client-custom-req-001"
    res = app_client.get("/health/live", headers={"X-Request-ID": client_id})
    assert res.headers.get("X-Request-ID") == client_id


def test_security_headers_present(app_client):
    """Verify defense-in-depth security headers on all responses."""
    res = app_client.get("/health/live")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "no-referrer"


def test_path_traversal_in_logs_rejected(app_client):
    """Verify directory traversal attempts in log content are blocked."""
    dangerous_payloads = [
        ["../../etc/shadow"],
        ["..\\..\\windows\\system32"],
        ["/etc/passwd"],
    ]
    for p in dangerous_payloads:
        res = app_client.post("/api/v1/analyze", json={"dataset": "hdfs", "logs": p})
        assert res.status_code == 422
        assert "forbidden filesystem path" in res.text


def test_label_leakage_blocked(app_client):
    """Verify forbidden ground-truth labels in request body are rejected."""
    forbidden_keys = [
        {"dataset": "hdfs", "logs": ["log"], "anomaly_label": 1},
        {"dataset": "hdfs", "logs": ["log"], "ground_truth": True},
        {"dataset": "hdfs", "logs": ["log"], "is_anomaly": False},
        {"dataset": "hdfs", "logs": ["log"], "target": 0},
    ]
    for p in forbidden_keys:
        res = app_client.post("/api/v1/analyze", json=p)
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "INVALID_REQUEST"


def test_citation_responses_contain_no_filesystem_paths(app_client):
    """Verify citation responses expose safe relative metadata without server paths."""
    payload = {
        "dataset": "hdfs",
        "logs": ["081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"],
        "options": {"window_id": "hdfs_session_blk_-7628164677193243450"},
    }
    res = app_client.post("/api/v1/analyze", json=payload)
    assert res.status_code == 200
    for cit in res.json()["citations"]:
        assert "source_file" not in cit
        assert "artifact_path" not in cit
        assert "data/" not in str(cit.values())


# ============================================================================
# 8. REGRESSION INTEGRITY TESTS
# ============================================================================

def test_phase7_regression_citations_intact():
    """Confirm Phase 7 authoritative citations are intact (HDFS: 117, BGL: 6)."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    service = PipelineService(cfg)
    hdfs_cits = sum(len(b.citations) for _, b, _ in service._cached_windows["hdfs"].values())
    bgl_cits = sum(len(b.citations) for _, b, _ in service._cached_windows["bgl"].values())
    assert hdfs_cits == 117
    assert bgl_cits == 6


def test_phase8_regression_decisions_intact():
    """Confirm Phase 8 authoritative decisions intact (HDFS: 33 INCIDENT, 6 SUSPICIOUS; BGL: 2 INSUFFICIENT_EVIDENCE)."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    service = PipelineService(cfg)
    hdfs_decisions = [a.decision for a, _, _ in service._cached_windows["hdfs"].values()]
    bgl_decisions = [a.decision for a, _, _ in service._cached_windows["bgl"].values()]
    assert hdfs_decisions.count("INCIDENT") == 33
    assert hdfs_decisions.count("SUSPICIOUS") == 6
    assert bgl_decisions.count("INSUFFICIENT_EVIDENCE") == 2


def test_phase9_regression_explanations_intact():
    """Confirm Phase 9 explanations intact and all evaluated as VERIFIED."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    service = PipelineService(cfg)
    hdfs_statuses = [e.faithfulness_status for _, _, e in service._cached_windows["hdfs"].values() if e]
    bgl_statuses = [e.faithfulness_status for _, _, e in service._cached_windows["bgl"].values() if e]
    assert all(s == "VERIFIED" for s in hdfs_statuses)
    assert all(s == "VERIFIED" for s in bgl_statuses)


def test_cors_origins_configurable():
    """Verify CORS origins can be explicitly configured via config."""
    cfg = ServingConfig.load("configs/phase10.yaml")
    cfg.server.cors_origins = ["https://triage.sentinellog.internal"]
    app = create_app(config=cfg)
    client = TestClient(app)

    res = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "https://triage.sentinellog.internal",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "https://triage.sentinellog.internal"
