# SentinelLog Cross-Origin Resource Sharing (CORS) Policy (Phase 14)

## 1. Overview

SentinelLog restricts browser cross-origin requests through explicit origin allowlisting. Wildcard CORS policies (`*`) are prohibited in production mode to prevent unauthorized cross-origin reading of triage results and credentials.

## 2. Configuration & Invariants

| Configuration Key | Env Override | Default |
| :--- | :--- | :--- |
| `cors_allowed_origins` | `SENTINELLOG_CORS_ALLOWED_ORIGINS` | `[]` (None allowed by default) |
| `enforce_production_mode` | `SENTINELLOG_ENFORCE_PRODUCTION_MODE` | `false` (dev) / `true` (prod) |

### Invariant 1: No Wildcard in Production (Rule 10, Rule 77)
If `SENTINELLOG_ENFORCE_PRODUCTION_MODE=true` and `SENTINELLOG_CORS_ALLOWED_ORIGINS` contains `*`, SentinelLog fails closed at application initialization:
```
ValueError: Security violation: Wildcard CORS ('*') is strictly forbidden in hardened production mode.
```

### Invariant 2: Explicit Allowlist for Frontend Dashboard
For development or deployed environments serving the Phase 11 Operator Dashboard, specific origins must be explicitly specified:
```yaml
security:
  cors_allowed_origins:
    - "http://localhost:5173"
    - "http://127.0.0.1:5173"
```
Or via environment variable:
```bash
export SENTINELLOG_CORS_ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

## 3. Rejection Behavior

When an unapproved origin (e.g. `Origin: http://malicious-site.com`) transmits a cross-origin request or preflight `OPTIONS` check:
1. SentinelLog does **not** return `Access-Control-Allow-Origin: http://malicious-site.com`.
2. The browser enforces the Same-Origin Policy and rejects response availability to malicious JavaScript.
3. Automated test suites verify both approved origin acceptance and malicious origin rejection.
