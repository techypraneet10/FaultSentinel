# SentinelLog Rollback Strategy & Recovery Procedures (Phase 15)

## 1. Overview

SentinelLog defines a rapid, deterministic rollback procedure to revert to the immediately preceding verified immutable release image whenever a deployment exhibits operational anomalies, elevated error rates, or readiness failures.

## 2. Automated Rollback Triggers (Rule 27)

Rollback is automatically or immediately triggered upon:
1. **ECS Deployment Circuit Breaker:** Tasks fail to reach healthy state on `/health/ready` within the deployment timeout window (default 10 minutes).
2. **Crash Loops:** Consecutive container exit codes non-zero or container restart threshold exceeded.
3. **Elevated 5xx Error Rate:** HTTP 5xx responses exceed 1% of total traffic over a 5-minute evaluation window.
4. **Readiness Probe Failure:** Unhealthy targets detected by the Application Load Balancer.

*Note: Research triage anomaly distribution differences do NOT trigger deployment rollback; operational telemetry and research evaluation are strictly separated.*

## 3. Rollback Procedure

### Step 1: Identify Target Preceding Release
Retrieve the immediately preceding verified release manifest from `results/phase15/releases/` or ECR tag catalog (e.g. `v0.14.0` / `sha256:abc123...`).

### Step 2: Halt Promotion & Execute Rollback
Execute the rollback utility to update the ECS service task definition:
```bash
python deploy/scripts/rollback.py \
  --env production \
  --tag v0.14.0 \
  --digest sha256:abc1234567890abcdef... \
  --reason "Elevated 5xx rate observed post-deployment" \
  --execute
```

### Step 3: Verify Traffic Cutover & Readiness
1. Monitor ECS service events as rolling update launches tasks running the previous image.
2. Confirm ALB target group reports new tasks as Healthy on `/health/ready`.
3. Terminate problematic release tasks after draining in-flight connections (30s timeout).

### Step 4: Validate via Smoke Tests
Run smoke tests against the restored production cluster:
```bash
python deploy/smoke/smoke_test.py --url https://sentinellog.internal --api-key $SENTINELLOG_API_KEY
```

## 4. Database Migration Rollback Considerations (Rule 62)

- Application rollback does **not** automatically revert database schema migrations.
- SentinelLog enforces **backward-compatible migrations** (expand-and-contract pattern):
  - New schema versions must remain fully compatible with N-1 application binaries.
  - Destructive schema drops are deferred until after the subsequent release cycle is confirmed stable.
