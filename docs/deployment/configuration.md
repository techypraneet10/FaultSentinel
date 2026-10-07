# SentinelLog Configuration & Validation (Phase 15)

## 1. Directory Structure

Deployment configurations are cleanly separated under `configs/`:
- `configs/development/app.yaml`: Local developer defaults.
- `configs/staging/app.yaml`: Staging environment parameters.
- `configs/production/app.yaml`: Hardened production parameters.

No secrets, passwords, or provider keys are committed to these files.

## 2. Configuration Validation (Rule 5)

Pre-flight and startup validation is enforced by `sentinellog.deployment.config_validator.validate_deployment_config`.

### Enforced Rules
- In staging and production:
  - `server.debug` must be `false` (Fail-closed).
  - `security.auth_enabled` must be `true`.
  - `security.enforce_production_mode` must be `true`.
  - `security.cors_allowed_origins` must be non-empty and must NOT contain wildcard (`*`).
  - `security.max_request_bytes` must be positive and $\le$ 10 MB.
  - `database.tls_required` must be `true`.
  - Required secret environment variables must be present.

### Pre-Deployment CLI Check
```bash
python deploy/scripts/validate_config.py --env production --check-env-vars
```
If any invariant fails, the application aborts immediately before accepting network traffic.

## 3. Environment Variables Reference

| Variable Name | Required | Description |
| :--- | :--- | :--- |
| `SENTINELLOG_ENV` | Yes | Target environment (`development`, `staging`, `production`) |
| `SENTINELLOG_AUTH_ENABLED` | Yes | `true` in staging/production |
| `SENTINELLOG_API_KEY` | Yes | Bearer token secret injected from Secrets Manager |
| `SENTINELLOG_CORS_ALLOWED_ORIGINS` | Yes | Comma-separated list of approved dashboard origins |
| `SENTINELLOG_REDIS_URL` | Staging/Prod | Redis connection URI for distributed rate limiting |
| `SENTINELLOG_DB_HOST` | Staging/Prod | Aurora PostgreSQL writer endpoint |
| `SENTINELLOG_DB_PASSWORD` | Staging/Prod | Database password injected from Secrets Manager |
| `SENTINELLOG_QDRANT_URL` | Staging/Prod | Qdrant Cloud cluster endpoint |
| `SENTINELLOG_QDRANT_API_KEY` | Staging/Prod | Qdrant authentication token |
| `SENTINELLOG_LLM_API_KEY` | Prod | OpenAI/Azure LLM provider API token |
| `SENTINELLOG_OTLP_ENDPOINT` | Staging/Prod | OpenTelemetry collector gRPC/HTTP endpoint |
