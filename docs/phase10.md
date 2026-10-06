# SentinelLog Phase 10: FastAPI Application & Serving Layer

## 1. Objective

Phase 10 implements the typed, asynchronous HTTP serving layer for SentinelLog, exposing the validated incident triage and explanation pipeline through an OpenAPI-compliant FastAPI service. 

**Core Architectural Rule:** Phase 10 is strictly an application and serving boundary. It does not contain custom anomaly detection, retrieval algorithms, reasoning heuristics, or prompt construction. The underlying research pipeline remains authoritative.

---

## 2. Architecture

The serving architecture enforces a fail-closed execution boundary:

```
[ HTTP Client Request ]
         ↓
[ Security & Size Middleware ] (Max 1MB, nosniff, DENY, no-referrer)
         ↓
[ Request ID Middleware ] (X-Request-ID propagation / UUID4)
         ↓
[ Pydantic Request Validation ] (dataset check, length bounds, path traversal guard, label leakage guard)
         ↓
[ AnalysisService ] (Application layer orchestration)
         ↓
[ PipelineService ] (Access to authoritative Phase 8 assessments & Phase 7 citations)
         ↓
[ Phase 8 Deterministic Reasoning ] (Immutable incident decision & severity)
         ↓
[ Phase 9 Grounded LLM Explanation ] (Verified claim grounding & citation checks)
         ↓
[ Response Validation & Serialization ] (AnalyzeResponse with safe coordinates)
         ↓
[ HTTP Response with X-Request-ID ]
```

---

## 3. API Endpoints

All application routes are strictly versioned under `/api/v1` or standard infrastructure health probe routes.

| Method | Path | Summary | Description |
|---|---|---|---|
| `GET` | `/health/live` | Process Liveness Probe | Returns `200 OK` if the process is alive. No expensive checks. |
| `GET` | `/health/ready` | Service Readiness Probe | Returns `200 OK` if pipeline models and authoritative calibration assets are loaded; `503 Service Unavailable` otherwise. |
| `GET` | `/api/v1` | Root Metadata | Returns public API version, application build version, and status without leaking internal paths. |
| `POST` | `/api/v1/analyze` | Log Sequence Analysis | Primary analysis endpoint accepting bounded log sequences. |

OpenAPI interactive documentation is automatically generated at `/docs` (Swagger UI) and `/redoc` (ReDoc), with machine-readable specifications available at `/openapi.json`.

---

## 4. Request Schemas

### `AnalyzeRequest`
```json
{
  "dataset": "hdfs",
  "logs": [
    "081109 203518 143 INFO dfs.DataNode DataXceiver: Receiving block blk_-7628164677193243450"
  ],
  "options": {
    "window_id": "hdfs_session_blk_-7628164677193243450",
    "include_citations": true,
    "include_raw_excerpts": false
  }
}
```

- `dataset`: Strictly `"hdfs"` or `"bgl"` (Literal). Any other value is rejected with `422 Unprocessable Entity`.
- `logs`: Non-empty list (`1 <= len <= 500`), where each line is bounded to at most 4096 characters.
- `options`: Optional `AnalysisOptions` model.
- `extra = "forbid"`: Disallows unverified arbitrary inputs.

---

## 5. Response Schemas

### `AnalyzeResponse`
```json
{
  "request_id": "8e5420f0-eaf2-4b05-afe9-67839d868e67",
  "status": "success",
  "dataset": "hdfs",
  "decision": "INCIDENT",
  "severity": "HIGH",
  "confidence": 0.92,
  "explanation_status": "GENERATED",
  "summary": "Executive summary...",
  "explanation": "Detailed grounded explanation...",
  "claims": [
    {
      "claim_id": "CLM-hdfs_session_blk-001",
      "claim_type": "OBSERVATION",
      "text": "The window exhibits repeated DataNode block transmission...",
      "citation_ids": ["305cfaab8b3fccbaaacf2a6255b779edfa33c7a16402d30bda41e2a283ffbd75"],
      "supported": true,
      "support_score": 0.2857
    }
  ],
  "citations": [
    {
      "citation_id": "305cfaab8b3fccbaaacf2a6255b779edfa33c7a16402d30bda41e2a283ffbd75",
      "dataset": "hdfs",
      "split": "train",
      "source_window_id": "hdfs_session_blk_123",
      "line_start": 100,
      "line_end": 150,
      "citation_text": null
    }
  ],
  "evidence_sufficiency": "SUFFICIENT",
  "provenance_status": "VERIFIED",
  "faithfulness_status": "VERIFIED",
  "processing_metadata": {
    "duration_ms": 31.04,
    "engine_version": "0.8.0",
    "model_name": "mock-deterministic-v1",
    "log_records_processed": 1
  }
}
```

---

## 6. Error Model

All API errors return a standard JSON envelope:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human-readable error explanation.",
    "request_id": "571fa153-f14e-4742-8c3a-690bcf9f976b",
    "details": {}
  }
}
```

### Standard Error Codes & Status Codes:
- `INVALID_REQUEST` (`400` / `422`): Malformed syntax or schema validation failure.
- `UNSUPPORTED_DATASET` (`422`): Dataset name outside `['hdfs', 'bgl']`.
- `PAYLOAD_TOO_LARGE` (`413`): Request body exceeds maximum allowed size.
- `SERVICE_UNAVAILABLE` (`503`): Readiness checks or dependencies not available.
- `PIPELINE_ERROR` (`500`): Pipeline component failure (decision immutability conflict, internal error).
- `INTERNAL_ERROR` (`500`): Unexpected server exception (stack traces and secrets suppressed).

---

## 7. Request IDs

- Every incoming HTTP request is assigned a unique tracking identifier.
- The service inspects incoming `X-Request-ID` headers (sanitized, alphanumeric + hyphen, $\le 128$ chars). If missing or invalid, a secure UUID4 is generated.
- The identifier is returned in the response header `X-Request-ID` and embedded in the `request_id` field of every response and structured log.

---

## 8. Configuration

Runtime behavior is defined in `configs/phase10.yaml` and loaded via `ServingConfig`:

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  environment: "production"
  log_level: "INFO"
  request_timeout: 30.0
  max_log_records: 500
  max_log_line_length: 4096
  max_request_bytes: 1048576  # 1 MB
  cors_origins: []
  api_version: "v1"

pipeline:
  data_root: "data/processed"
  results_root: "results"
  phase7_results: "results/phase7"
  phase8_results: "results/phase8"
  phase9_results: "results/phase9"
  supported_datasets:
    - "hdfs"
    - "bgl"

explanation:
  provider: "mock"
  model_name: "mock-deterministic-v1"
  timeout_sec: 15.0
```

Environment variable overrides are prefixed with `SENTINELLOG_`:
- `SENTINELLOG_HOST`
- `SENTINELLOG_PORT`
- `SENTINELLOG_ENV`
- `SENTINELLOG_LOG_LEVEL`
- `SENTINELLOG_CORS_ORIGINS`
- `SENTINELLOG_MAX_LOG_RECORDS`
- `SENTINELLOG_MAX_LOG_LINE_LENGTH`
- `SENTINELLOG_MAX_REQUEST_BYTES`
- `SENTINELLOG_REQUEST_TIMEOUT`

---

## 9. Security Boundaries

1. **No Client API Keys:** The API does not accept LLM provider credentials or API keys in requests. All LLM credentials originate strictly from server-side environment variables.
2. **Filesystem Isolation:** Clients cannot submit local filesystem paths or select internal files. Any string containing relative traversal (`../`, `..\`) or absolute drives (`C:\`, `/etc/`) is rejected with `422`.
3. **No Ground Truth / Label Leakage:** The request schema explicitly forbids ground-truth keys (`anomaly_label`, `ground_truth`, `is_anomaly`, `target`, `label`). Any attempt to submit them fails validation.
4. **Information Suppression:** Citations expose relative coordinates (`dataset`, `split`, `source_window_id`, `line_start`, `line_end`). Absolute filesystem paths and internal stack traces are strictly stripped.
5. **Security Headers:** Middleware automatically applies `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`.
6. **CORS:** Defaults to an empty list `[]` (no wildcard `*` default).

---

## 10. Payload Limits

- Max request body bytes: 1,048,576 bytes (1 MB), enforced by `SecurityHeadersMiddleware`. Oversized requests receive `413 Payload Too Large`.
- Max log records: 500 records per request.
- Max log line length: 4,096 characters per record.

---

## 11. Timeouts

- Pipeline execution bounds are enforced via `request_timeout` (default: 30.0s).
- Underlying LLM provider calls respect Phase 9 `timeout_sec` (default: 15.0s).

---

## 12. Dependency Injection

FastAPI dependency providers (`sentinellog/serving/dependencies.py`):
- `get_config`: Injects `ServingConfig`.
- `get_pipeline_service`: Injects shared `PipelineService` singleton.
- `get_analysis_service`: Injects `AnalysisService`.
- `get_request_id`: Extracts request tracking ID.

This architecture enables seamless dependency overrides in unit and integration test suites without spinning up external servers.

---

## 13. Testing

The Phase 10 test suite covers:
- Application factory initialization, OpenAPI schemas, and versioning.
- Health liveness and readiness probe responses, including failure modes.
- Strict input validation: empty logs, unsupported datasets, oversized logs, oversized lines, malformed JSON, and unexpected fields.
- Security controls: path traversal rejection, label leakage rejection, security headers, request ID propagation, and absence of internal secrets.
- Analysis pipeline execution: HDFS incident evaluation, BGL `INSUFFICIENT_EVIDENCE` preservation, and citation coordinate safety.
- Decision immutability and severity preservation.
- Error handling: domain exceptions, pipeline errors, and unhandled 500 formatting.

---

## 14. OpenAPI

OpenAPI metadata is fully documented with descriptions, examples, and schemas for request/response models. Generated schemas comply with OpenAPI 3.1.0 specifications.

---

## 15. Phase 9 Integration

`PipelineService` directly consumes the output of Phase 9's `ExplanationOrchestrator`, maintaining the invariant that all returned factual claims are grounded by verified Phase 7 citations with verified provenance.

---

## 16. Phase 11 Interface

Phase 11 (Triage Frontend) interfaces strictly with the Phase 10 API via:
`POST /api/v1/analyze`
Receiving structured responses containing `decision`, `severity`, `confidence`, `explanation`, `claims`, and `citations`. Phase 11 requires no direct dependency on internal models or data paths.

---

## 17. Limitations & Future Scope

- **Stateless Serving:** Phase 10 is stateless. Persistent session history and database storage are outside Phase 10.
- **Authentication:** Token-based authentication (OAuth2 / JWT) and user management are not implemented in Phase 10 and represent future deployment concerns.
- **Rate Limiting:** Production distributed rate limiting (e.g. Redis token buckets) is deferred to deployment phases; Phase 10 implements bounded payload enforcement.
