# SentinelLog Phase 13 Documentation: Observability & Reliability

## 1. Observability Architecture
SentinelLog Phase 13 implements an observability layer that observes the triage pipeline without steering it. Telemetry components capture metrics, logs, traces, and diagnostics without altering decisions, scores, thresholds, retrieval candidates, citations, or grounded explanations.

```
Request (X-Request-ID)
      ↓
ObservabilityMiddleware (Tracing root span, access log, latency, status metric)
      ↓
FastAPI Router (/api/v1/analyze, /metrics, /health/*, /api/v1/diagnostics)
      ↓
Analysis Service (Stage spans: analysis, selective gate, provenance, reasoning, explanation)
      ↓
Observability Subsystems
  ├── Structured JSON Logging (Contextual request_id, centralized secret redactor)
  ├── Distributed Tracing (In-memory bounded buffer, parent-child spans, OpenTelemetry compatible)
  ├── Prometheus Metrics Registry (/metrics exposition, bounded cardinality controls)
  └── Safe Diagnostics (/api/v1/diagnostics, candidate SLIs)
```

## 2. Structured Logging
Every request emits structured JSON log records containing:
- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log level (INFO, DEBUG, ERROR)
- `service`: `sentinellog`
- `environment`: Runtime environment (e.g., `development`)
- `request_id`: Contextual correlation ID propagated from `X-Request-ID`
- `trace_id` & `span_id`: Associated active trace context
- `event`: Standardized event taxonomy name
- `duration_ms`: Operational latency in milliseconds
- `status`: Execution status (`success`, `failure`)

## 3. Event Taxonomy
Stable operational event names:
- `application_started`, `application_shutdown`
- `request_started`, `request_completed`, `request_rejected`
- `analysis_started`, `analysis_completed`, `analysis_failed`
- `ingestion_started`, `ingestion_completed`, `ingestion_failed`
- `scoring_started`, `scoring_completed`, `scoring_failed`
- `gate_auto_clear`, `gate_escalate`
- `retrieval_started`, `retrieval_completed`, `retrieval_failed`
- `reranking_started`, `reranking_completed`, `reranking_failed`
- `provenance_started`, `provenance_verified`, `provenance_rejected`
- `reasoning_started`, `reasoning_completed`, `reasoning_failed`
- `explanation_started`, `explanation_completed`, `explanation_failed`
- `provider_timeout`, `provider_error`
- `validation_failed`
- `health_check`, `readiness_failed`

## 4. Metrics
Prometheus-compatible metrics exposed at `GET /metrics`:
- `request_count`, `request_errors`, `http_requests_by_family`, `request_latency`
- `analysis_count`, `analysis_errors`, `analysis_latency`
- `ingestion_count`, `ingestion_failures`
- `scoring_count`, `scoring_failures`
- `auto_clear_count`, `escalation_count`, `escalation_rate`
- `retrieval_count`, `retrieval_failures`
- `reranking_count`
- `provenance_count`, `provenance_verified_total`, `provenance_rejected_total`, `citation_validation_failures`
- `reasoning_count`, `reasoning_failures`, `decisions_total`
- `explanation_count`, `explanation_generated_total`, `explanation_failed_total`, `explanation_skipped_total`, `faithfulness_verified_total`, `faithfulness_failed_total`
- `llm_requests_total`, `llm_success_total`, `llm_failure_total`, `llm_timeout_total`, `llm_calls_by_dataset`, `llm_latency`
- Stage latency histograms: `retrieval_latency`, `reranking_latency`, `provenance_latency`, `reasoning_latency`, `explanation_latency`

## 5. Tracing
- OpenTelemetry-compatible in-memory tracing engine.
- Bounded memory buffer (default 1000 spans) with FIFO eviction.
- Standard context propagation with `trace_id` and `span_id`.
- Support for configurable sampling rate (0.0 to 1.0).

## 6. Correlation IDs
- Standard `X-Request-ID` HTTP header reused across the entire pipeline.
- Propagated through `contextvars` to all log records and span attributes.

## 7. Health & Readiness
- `GET /health/live`: Fast process liveness probe (200 OK).
- `GET /health/ready`: Pipeline readiness checking authoritative models and calibration assets (503 if unavailable).
- `GET /health/observability`: Telemetry readiness reporting logging, metrics, and tracing statuses.

## 8. Error Taxonomy
Operational reliability error categories:
- `CLIENT_ERROR`
- `VALIDATION_ERROR`
- `PIPELINE_ERROR`
- `RETRIEVAL_ERROR`
- `PROVENANCE_ERROR`
- `REASONING_ERROR`
- `EXPLANATION_ERROR`
- `PROVIDER_TIMEOUT`
- `PROVIDER_ERROR`
- `CONFIGURATION_ERROR`
- `DEPENDENCY_ERROR`
- `INTERNAL_ERROR`

## 9. Redaction
Centralized regex redaction scrubs sensitive patterns from strings, dictionaries, log records, and span attributes:
- `Bearer <token>`
- `api_key=...` / `apikey=...`
- `secret=...`
- `password=...`
- `authorization=...`

## 10. Cardinality Controls
Metric labels are strictly bounded to finite sets:
- `dataset`: `hdfs`, `bgl`
- `status`: `success`, `failure`
- `endpoint`: finite route set
- `decision`: `NORMAL`, `SUSPICIOUS`, `INCIDENT`, `INSUFFICIENT_EVIDENCE`
- `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- Unbounded identifiers (`request_id`, raw log lines, citation IDs) are explicitly filtered and never used as Prometheus label dimensions.

## 11. Sampling
Tracing sampling is configurable via `SENTINELLOG_TRACE_SAMPLE_RATE` (0.0 to 1.0). Default is 1.0 for local evaluation.

## 12. Reliability Behavior
Fail-closed policy:
- If retrieval or provenance fails, citations are not marked verified.
- If explanation or LLM fails, deterministic Phase 8 reasoning decision is preserved and explanation marked FAILED.

## 13. Timeout & Retry Behavior
- Request timeout: 30s
- LLM timeout: 15s
- Max retries: 2 (conservative bounded retry for external provider calls only; deterministic reasoning is never retried).

## 14. Telemetry Failure Isolation
Critical rule: telemetry failure must never become application failure.
- Metric collection errors are caught and suppressed.
- Tracing buffer exceptions are caught and suppressed.
- Logging formatting errors fall back to raw message logging.

## 15. Configuration
Configured via `configs/phase13.yaml` and environment variables with `SENTINELLOG_` prefix:
- `SENTINELLOG_LOG_LEVEL`
- `SENTINELLOG_JSON_LOGGING`
- `SENTINELLOG_METRICS_ENABLED`
- `SENTINELLOG_TRACING_ENABLED`
- `SENTINELLOG_OTLP_ENDPOINT`
- `SENTINELLOG_TRACE_SAMPLE_RATE`

## 16. Local Development
Runs purely locally using in-memory telemetry buffers and standard Python runtime. Zero cloud, Jaeger, Tempo, or external Prometheus server dependencies required.

## 17. Security Considerations
- Zero secrets or bearer tokens logged.
- Bounded diagnostic exposition: no environment variables, file paths, or credentials leaked via `/api/v1/diagnostics` or `/metrics`.

## 18. Performance Overhead
Benchmarked overhead:
- Telemetry enabled median: 8.78 ms
- Telemetry disabled median: 8.61 ms
- Overhead: 0.18 ms

## 19. Testing
Comprehensive test suite (`tests/test_observability.py`) covering 46 test cases across structured logging, redaction, tracing, metrics, cardinality, failure isolation, and lifecycle deadlock regression.

## 20. Phase 14 Interface
Phase 13 delivers structured logs, metrics, traces, health probes, and reliability diagnostics. Phase 14 will build on this interface to implement security hardening, authentication, authorization, secret management, and rate limiting.
