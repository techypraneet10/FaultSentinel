# SentinelLog Production Release Checklist (Phase 15)

## 1. Pre-Release Verification (CI Stage)

- [ ] All 410+ backend Python unit and integration tests passing (`pytest`).
- [ ] All 50 frontend Vitest component and integration tests passing (`npm test`).
- [ ] TypeScript compilation succeeds with zero errors (`tsc --noEmit`).
- [ ] Frontend linter exits cleanly (`npm run lint`).
- [ ] Python bytecode compiles without errors (`python -m compileall sentinellog tests`).
- [ ] All 55 Phase 14 security tests passing (`tests/test_security.py`).
- [ ] Secret scanner finds 0 high-confidence credentials (`scan_repository`).
- [ ] Dependency audit shows 0 high/critical remote code vulnerabilities.
- [ ] Frozen Phase 12 benchmark hashes match authoritative records ($N=823$ HDFS, $N=100$ BGL).

## 2. Image Build & Scan

- [ ] Docker image built from multi-stage hardened `Dockerfile`.
- [ ] Image executes under unprivileged system user (`USER 10001:10001`).
- [ ] Image pushed to Amazon ECR with immutable semantic version tag and digest.
- [ ] ECR vulnerability scan returns zero critical/high findings.

## 3. Staging Deployment & Smoke Testing

- [ ] Terraform applied to `infra/environments/staging/`.
- [ ] Staging ECS service updated with new immutable image digest.
- [ ] ALB target group health checks on `/health/ready` report healthy.
- [ ] Automated smoke test suite passes (`deploy/smoke/smoke_test.py`).
- [ ] Verified that Staging and Production do not share any data or credentials.

## 4. Production Release Gate & Rollout

- [ ] Production release manifest generated and signed in `results/phase15/`.
- [ ] Release approval received from designated technical operator.
- [ ] Production ECS rolling deployment triggered (min healthy 100%, max 200%).
- [ ] ECS Deployment Circuit Breaker active with automated rollback.
- [ ] Production ALB target group healthy.
- [ ] Production smoke tests execute successfully.
- [ ] Real-time error rate and p95 latency monitored for 30 minutes post-deployment.
