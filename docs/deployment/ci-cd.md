# SentinelLog CI/CD Pipeline & Automated Gates (Phase 15)

## 1. Pipeline Overview

SentinelLog enforces a 13-stage deterministic Continuous Integration (CI) pipeline alongside a staged release workflow. A failure in any stage immediately halts promotion.

## 2. CI Pipeline Stages

```
1. Checkout
   ↓
2. Dependencies (Python 3.12, Node.js 20)
   ↓
3. Backend Test Suite (Pytest: 410+ tests)
   ↓
4. Frontend Test Suite (Vitest: 50 tests)
   ↓
5. Frontend Typecheck (tsc --noEmit)
   ↓
6. Frontend Lint (ESLint)
   ↓
7. Python Bytecode (compileall)
   ↓
8. Security Tests (Phase 14 Test Suite)
   ↓
9. Secret Scanning (Zero-secrets scan)
   ↓
10. Dependency Vulnerability Audit (npm audit & pip inspect)
   ↓
11. Docker Image Build (Multi-stage non-root)
   ↓
12. Container Security Verification (UID 10001 & Healthcheck)
   ↓
13. Release Manifest & Artifact Validation
```

## 3. Promotion Gates & Environments

1. **Pull Request Gate:** Stages 1–12 must be 100% green before code can merge to `master`.
2. **Staging Promotion Gate:** Merged commits or tagged releases deploy automatically to Staging Fargate.
3. **Smoke Test Gate:** Automated `deploy/smoke/smoke_test.py` executes against Staging `/health/live`, `/health/ready`, `/api/v1/analyze`, and `/metrics`.
4. **Production Gate:** Requires green staging smoke tests, immutable release manifest generation, and manual operator approval before rolling update to Production.
