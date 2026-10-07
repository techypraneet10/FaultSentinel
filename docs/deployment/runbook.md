# SentinelLog Production Operator Runbook (Phase 15)

## 1. Daily Operations & Routine Checks

### Inspect Service Health
```bash
# Public liveness probe (checks process responsiveness)
curl -sS https://sentinellog.internal/health/live

# Readiness probe (checks pipeline assets and dependencies)
curl -sS https://sentinellog.internal/health/ready
```

### Inspect Observability Telemetry
```bash
# Subsystem telemetry status
curl -sS https://sentinellog.internal/health/observability

# Prometheus operational metrics (requires operator Bearer token)
curl -sS -H "Authorization: Bearer $SENTINELLOG_API_KEY" https://sentinellog.internal/metrics

# Safe system diagnostics
curl -sS -H "Authorization: Bearer $SENTINELLOG_API_KEY" https://sentinellog.internal/api/v1/diagnostics
```

## 2. Standard Deployment Procedure

1. **Pre-flight Configuration Verification:**
   ```bash
   python deploy/scripts/validate_config.py --env production --check-env-vars
   ```
2. **Trigger Rolling Deployment in AWS ECS:**
   ```bash
   aws ecs update-service \
     --cluster sentinellog-production-cluster \
     --service sentinellog-production-service \
     --task-definition sentinellog-production:15 \
     --force-new-deployment
   ```
3. **Monitor Rolling Update:**
   ```bash
   aws ecs wait services-stable \
     --cluster sentinellog-production-cluster \
     --services sentinellog-production-service
   ```
4. **Execute Post-Deployment Smoke Tests:**
   ```bash
   python deploy/smoke/smoke_test.py --url https://sentinellog.internal --api-key $SENTINELLOG_API_KEY
   ```

## 3. Incident Response & Emergency Procedures

### 3.1 Initiating Immediate Rollback
If elevated errors or task instability occur:
```bash
python deploy/scripts/rollback.py \
  --env production \
  --tag v0.14.0 \
  --digest sha256:7f9b8c1a... \
  --reason "Incident SEV-2: elevated 5xx rate detected" \
  --execute
```

### 3.2 Secret Rotation (API Key or LLM Provider)
1. Update secret in AWS Secrets Manager:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id sentinellog/production/api_key \
     --secret-string '{"SENTINELLOG_API_KEY":"new-high-entropy-token-123456"}'
   ```
2. Trigger graceful rolling task restart to reload new credentials into Fargate tasks:
   ```bash
   aws ecs update-service \
     --cluster sentinellog-production-cluster \
     --service sentinellog-production-service \
     --force-new-deployment
   ```

### 3.3 External LLM Provider Outage
- SentinelLog Phase 8 deterministic reasoning remains authoritative and continues to operate unaffected.
- Explanations gracefully degrade and flag `PROVIDER_UNAVAILABLE`.
- No restart required; retries are bounded and circuit breakers prevent cascade failures.

### 3.4 Database or Vector Database Degradation
- Check CloudWatch Aurora metric `CPUUtilization` and `ServerlessDatabaseCapacity`.
- Check Qdrant Cloud cluster health.
- If database connection drops, `/health/ready` returns HTTP 503, preventing traffic routing to degraded instances while preserving in-flight requests.
