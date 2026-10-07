# SentinelLog Authorization & Endpoint Access (Phase 14)

## 1. Minimal Role Model

SentinelLog employs a lean, explicit three-tier role model tailored to operational needs without unnecessary RBAC complexity:

1. **`admin`**: Full administrative access across all endpoints, configuration, diagnostics, and metrics.
2. **`analyst`**: Access to incident triage analysis (`/api/v1/analyze`), API documentation, and basic health probes. Restricted from operational diagnostics and metrics.
3. **`operator`**: Access to telemetry, Prometheus metrics (`/metrics`), safe diagnostics (`/api/v1/diagnostics`), and readiness probes (`/health/ready`, `/health/observability`). Restricted from incident triage submission.
4. **`public`**: Unauthenticated access restricted strictly to liveness probe (`/health/live`).

## 2. Endpoint Protection Matrix

| Endpoint | Classification | Minimum Role | Notes |
| :--- | :--- | :--- | :--- |
| `/health/live` | **Public** | `public` / Any | Light probe confirming process uptime. Zero secrets or paths. |
| `/health/ready` | **Operational** | `operator` / Public* | Verifies model & calibration loading without exposing paths. |
| `/health/observability` | **Operational** | `operator` / Public* | Reports telemetry subsystem health status. |
| `/docs`, `/redoc`, `/openapi.json` | **Documentation** | `analyst`, `admin` | OpenAPI schema exploration. |
| `/api/v1/analyze` | **Protected** | `analyst`, `admin` | Core triage pipeline execution. |
| `/metrics` | **Protected** | `operator`, `admin` | Prometheus exposition endpoint. |
| `/api/v1/diagnostics` | **Protected** | `operator`, `admin` | Safe diagnostic telemetry & candidate SLIs. |

*\* Note: In hardened mode, operational probes return sanitized status suitable for ingress monitoring.*

## 3. Authorization Failures & Responses

When an authenticated client attempts to access an endpoint outside its assigned role, SentinelLog immediately rejects the request with **HTTP 403 Forbidden**:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Endpoint requires 'operator' or 'admin' role.",
    "request_id": "req-209481",
    "details": {
      "role": "analyst"
    }
  }
}
```

### Telemetry Integration
Every authorization denial increments the bounded Prometheus counter `authorization_denials_total` and logs a structured event `authorization_denied` with client request correlation ID.
