# SentinelLog Security Incident Response Plan (Phase 14)

## 1. Scope & Objective

This document outlines the standard operational procedure for detecting, containing, remediating, and recovering from security incidents involving SentinelLog API serving, credentials, or underlying models.

## 2. Incident Classification & Severity

| Severity | Definition | Examples | Response Target |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Active compromise of API credentials, remote code execution vulnerability, unauthorized alteration of model calibration artifacts. | Stolen production API key actively utilized; unauthorized file write. | Immediate (< 1 hour) |
| **SEV-2 (High)** | Denial of service, rate limit evasion, prompt injection subverting triage logic, confirmed dependency CVE with known exploit. | Malicious client flooding API; unexpected high memory consumption. | < 4 hours |
| **SEV-3 (Medium)** | Information disclosure (e.g. non-sensitive internal error snippet), suspicious unauthenticated scan traffic. | Unauthenticated port scan, malformed request bursts. | < 24 hours |

## 3. Incident Playbooks

### 3.1 Credential Compromise & Rotation Playbook
1. **Identification:** Detect compromised token in external leaks, public logs, or unauthorized client requests.
2. **Containment:**
   - Invalidate the current token immediately by replacing `SENTINELLOG_API_KEY` in environment secrets management.
   - Restart the serving instances to reload `SecurityConfig`.
3. **Investigation:** Inspect structured logs for `authentication_failed` and `request_rejected` events matching the compromised token identifier.
4. **Recovery:** Issue new cryptographic key (minimum 32 random alphanumeric characters) to authorized operators.

### 3.2 Suspicious / Abusive API Activity (DoS / Rate Limiting)
1. **Identification:** Sustained spike in `rate_limit_exceeded_total` metrics or high HTTP 429 response frequency.
2. **Containment:**
   - Verify `RateLimiter` memory state via `/api/v1/diagnostics`.
   - Update reverse proxy / firewall rules to block abusive IP addresses upstream before hitting SentinelLog.
   - Temporarily lower `SENTINELLOG_RATE_LIMIT_REQUESTS` if necessary.
3. **Recovery:** Confirm resource stabilization (CPU/memory) and resume normal window policies.

### 3.3 Adversarial Log Input & Prompt Injection Attempt
1. **Identification:** Detection of adversarial instructions (`"Ignore previous instructions"`, `"Reveal API key"`) in submitted logs.
2. **Containment:**
   - Confirm Phase 8 deterministic reasoning was not bypassed.
   - Confirm Phase 9 claim verification flagged ungrounded claims or that citations remained strictly grounded.
3. **Remediation:** Add adversarial patterns to regression test suite `tests/test_security.py`.

### 3.4 Dependency Vulnerability Disclosure
1. **Identification:** New advisory in Python or Node.js ecosystem.
2. **Assessment:** Verify whether affected component is used in active codepaths and whether exposure exists behind SentinelLog's input validation boundary.
3. **Remediation:** Update pinned version in `requirements.txt` or `package-lock.json`, run test suite to ensure no regressions, and deploy updated container.

## 4. Evidence Preservation & Post-Incident Review

- Retain structured audit logs and Prometheus time-series snapshots for forensic review.
- Document timeline, root cause, impact, and preventive actions in `results/phase14/`.
