# SentinelLog Authentication Architecture (Phase 14)

## 1. Overview

SentinelLog provides configurable, constant-time API token authentication designed to protect serving endpoints from unauthenticated access while supporting flexible local development and fail-closed production deployment.

## 2. Configuration & Modes

Authentication behavior is controlled via environment variables or YAML configuration:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `SENTINELLOG_AUTH_ENABLED` | bool | `false` (dev) / `true` (prod) | Toggles API token authentication requirement. |
| `SENTINELLOG_API_KEY` | string | `null` | Primary administrative API key (minimum 8 characters). |
| `SENTINELLOG_ANALYST_API_KEY` | string | `null` | Analyst role key (restricted to triage analysis endpoints). |
| `SENTINELLOG_OPERATOR_API_KEY` | string | `null` | Operator role key (restricted to metrics & diagnostics). |
| `SENTINELLOG_ENFORCE_PRODUCTION_MODE` | bool | `false` | When true, enforces strict invariants (fails startup if auth is disabled or key is missing). |

### Fail-Closed Principle (Rule 76)
If `SENTINELLOG_AUTH_ENABLED=true` and `SENTINELLOG_API_KEY` is missing, empty, or shorter than 8 characters, SentinelLog **fails startup immediately with a fatal configuration exception**. The application will never silently fall back to unauthenticated operation.

## 3. Credential Submission & Headers

Clients authenticate by supplying the token in the standard HTTP `Authorization` header:

```http
POST /api/v1/analyze HTTP/1.1
Host: api.sentinellog.local
Authorization: Bearer sec-token-xyz-1234567890
Content-Type: application/json
```

Legacy integration header `X-API-Key: sec-token-xyz-1234567890` is also accepted as a fallback.

## 4. Constant-Time Verification

To mitigate timing side-channel attacks, token comparison utilizes `hmac.compare_digest`:

```python
def verify_api_key(provided_token: Optional[str], expected_token: str) -> bool:
    if not provided_token or not expected_token:
        return False
    return hmac.compare_digest(provided_token.encode("utf-8"), expected_token.encode("utf-8"))
```

Execution duration is invariant with respect to the number of matching leading bytes.

## 5. Error Responses

Unauthenticated requests receive HTTP 401 without leaking internal system state:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Valid API key or Bearer token required for access.",
    "request_id": "req-984210",
    "details": {
      "reason": "authentication_required"
    }
  }
}
```

Authentication errors increment the `authentication_failures_total` Prometheus counter and emit structured audit events without logging credential values.
