# SentinelLog Threat Model (Phase 14)

## 1. Executive Summary

SentinelLog is a calibrated selective prediction system for LLM-assisted incident triage over system logs. This threat model defines the security boundaries, assets, threat actors, and defensive controls that safeguard SentinelLog without modifying the underlying research methodology or frozen statistical claims.

## 2. System Architecture & Trust Boundaries

```
[ Untrusted Client / Browser ]
           │
═══════════╪══════════════════════════════════════════════════════ [ Trust Boundary 1: Perimeter / Ingress ]
           ▼
[ FastAPI Ingress + Security Middleware ]
  - Rate Limiting (Sliding Window, Bounded Storage)
  - Content-Length Bounds (Early 413 Rejection)
  - Constant-Time Token Authentication (HMAC digest)
  - Role-Based Endpoint Authorization (403 Forbidden)
  - Security Headers (CSP, nosniff, DENY, no-referrer)
           │
═══════════╪══════════════════════════════════════════════════════ [ Trust Boundary 2: Application Services ]
           ▼
[ SentinelLog Research & Serving Pipeline ]
  - Phase 4: Calibrated Selective Prediction
  - Phase 5: Semantic & Lexical Log Retrieval
  - Phase 6: Maximal Marginal Relevance Reranking
  - Phase 7: Strict Provenance Mapping & Verification
  - Phase 8: Authoritative Deterministic Reasoning
  - Phase 9: Grounded LLM Explanation & Faithfulness
           │
═══════════╪══════════════════════════════════════════════════════ [ Trust Boundary 3: Internal Assets & Providers ]
           ├── Local File System (Strict Path Traversal Boundary: data/, results/, configs/)
           ├── Observability Telemetry (Redacted Logging, Metrics, Traces)
           └── External LLM Provider (Isolated Sandboxing & Mock Provider)
```

## 3. Protected Assets

| Asset Category | Description | Sensitivity |
| :--- | :--- | :--- |
| **API Credentials** | Static API keys and Bearer tokens | High (Confidentiality) |
| **Provider Credentials** | External LLM provider API tokens | High (Confidentiality) |
| **Model & Calibration Artifacts** | Scorer weights, conformal nonconformity scores, thresholds | Critical (Integrity) |
| **Evaluation Benchmark Data** | Frozen Phase 12 ground truth, evaluation splits, benchmark metrics | Critical (Integrity) |
| **Raw & Retrieved Logs** | System log windows, evidence text, citations | Medium (Confidentiality / Untrusted Input) |
| **Telemetry & Observability** | Prometheus metrics, trace spans, structured JSON events | Medium (Integrity / Confidentiality) |
| **Application Runtime** | Process memory, host filesystem, non-root container environment | High (Availability / Integrity) |

## 4. Threat Actors & Attack Vectors

### 4.1 Unauthenticated Internet Client
- **Objective:** Probe endpoints, execute Denial of Service (DoS), leak system diagnostics.
- **Defenses:** Constant-time authentication on protected routes (`/api/v1/analyze`, `/api/v1/diagnostics`, `/metrics`), sliding-window rate limiting, early 413 payload truncation, and minimal unauthenticated responses on `/health/live`.

### 4.2 Malicious Authenticated User
- **Objective:** Escalate privileges, access unauthorized administrative diagnostics, or exceed rate limits.
- **Defenses:** Role authorization matrix (`analyst`, `operator`, `admin`), bounded rate limiting per authenticated identity, strict input validation forbidding extra fields (`extra='forbid'`).

### 4.3 Malicious Log Content & Prompt Injection
- **Objective:** Subvert triage reasoning, bypass provenance verification, fabricate citations, or extract API keys via adversarial log strings (e.g., `"Ignore previous instructions"`, `"<script>alert(1)</script>"`).
- **Defenses:** Log content treated strictly as untrusted data. Phase 8 deterministic reasoning is completely isolated from LLM output. Phase 9 prompt isolation treats logs purely as quotation blocks; claim-level citation validation verifies evidence independently; raw execution or shell interpretation of log lines is strictly barred.

### 4.4 Path Traversal & Filesystem Manipulation
- **Objective:** Escape application directories to read `.env`, configuration secrets, or system files (`/etc/passwd`, `C:\Windows`).
- **Defenses:** Strict `PathValidator` employing `pathlib.Path.resolve()` against an explicit allowlist of directory roots (`data`, `results`, `configs`). Prohibits relative traversal components (`..`, `..\`, `%2e%2e`).

### 4.5 Secret & Credential Leakage
- **Objective:** Exfiltrate API tokens through logs, exception tracebacks, metrics exposition, or source commits.
- **Defenses:** Automated regex-based secret scanning in CI/tests, sanitized API error responses (zero stack traces or internal paths), and structured logging redaction filters.

### 4.6 Insecure Browser & Cross-Origin Interactions
- **Objective:** Cross-Site Scripting (XSS), Clickjacking, or unauthorized CORS requests.
- **Defenses:** Strict Content Security Policy (`CSP`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and explicit, non-wildcard CORS origin enforcement.
