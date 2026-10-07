# FaultSentinel v1.1 Feature Overview

## Executive Summary
FaultSentinel v1.1 transforms FaultSentinel from an anomaly detector into an **AI Incident Investigation & Reliability Workbench**.

The core scientific inference engine remains completely frozen and validated:
- Anomaly scoring ($B0 / B1 / B2$)
- Split conformal calibration ($\alpha = 0.05$)
- Dense vector retrieval (train split only)
- MMR evidence diversification ($\lambda = 0.5$)
- Dual-hash provenance engine
- Deterministic expert reasoning (Phase 8)
- Programmatic faithfulness verification (Phase 9)

FaultSentinel v1.1 layers non-invasive, auditable, and interactive capabilities designed specifically for SRE triage, reliability analysis, and recruiter walkthroughs.

---

## The 5 Primary Features

### 1. Incident Replay Lab
A step-by-step 11-stage visualization layer over actual recorded execution telemetry:
- `01_INGEST` $\rightarrow$ `02_PARSE` $\rightarrow$ `03_WINDOW` $\rightarrow$ `04_SCORE` $\rightarrow$ `05_CONFORMAL` $\rightarrow$ `06_RETRIEVE` $\rightarrow$ `07_MMR` $\rightarrow$ `08_PROVENANCE` $\rightarrow$ `09_REASONING` $\rightarrow$ `10_LLM` $\rightarrow$ `11_VERIFY`.
- Playback controls: First, Previous, Play (0.5x, 1x, 2x), Pause, Next, Last.
- Stage Inspector: inputs, outputs, latency, failure modes, and implementation source links.
- "Why Escalated?" analytical inspector and counterfactual simulation.

### 2. Fault Injection & Reliability Lab
Controlled reliability testing simulating 9 dependency outages in local/staging environments:
- LLM provider timeout & fallback to deterministic diagnosis.
- Retrieval unavailable & fallback to `INSUFFICIENT_EVIDENCE`.
- Ingestion rejection on oversized payloads (HTTP 422).
- Parser error handling on malformed JSON (HTTP 422).
- Faithfulness failure triggering ungrounded claim warnings.
- Authentication & authorization failures (HTTP 401 & 403).
- Configuration validation schema assertions.
- Production guard: automatically locks and disables fault execution in production.

### 3. Calibration Drift Monitor
Observational statistical monitor for conformal anomaly score distribution:
- Population Stability Index (PSI) over reference quantile bins ($PSI < 0.10$ Stable, $0.10 \le PSI < 0.25$ Watch, $PSI \ge 0.25$ Drift).
- Quantile shifts ($p25, p50, p75, p90, p99$).
- Escalation rate vs. nominal reference $\alpha$ comparison.
- Distribution comparison histogram (white = reference, gray = current, amber = watch, red = drift).
- Strict Rule 25: Never automatically recalibrates; enforces an 8-step review workflow.

### 4. Evidence Graph
Interactive 10-node directed provenance graph:
`INCIDENT` $\rightarrow$ `WINDOW` $\rightarrow$ `SCORE` $\rightarrow$ `DECISION` $\rightarrow$ `RETRIEVAL` $\rightarrow$ `EVIDENCE CHUNKS` $\rightarrow$ `PROVENANCE` $\rightarrow$ `REASONING` $\rightarrow$ `LLM CLAIM` $\rightarrow$ `CITATION` $\rightarrow$ `SOURCE LOG`.
- Real cryptographic hashes (`source_content_hash`, `template_content_hash`).
- Verifies that all citations originate strictly from the chronological train split.

### 5. Decision Passport
Compact, tamper-evident cryptographic document locking every automated decision to its provenance:
- SHA-256 Decision Hash binding score, threshold, severity, evidence hash, configuration hash, and git commit.
- Verification endpoint and copy/export JSON/Markdown formats.

---

## Additional Capabilities

### Human Adjudication
Lightweight SRE review (`CONFIRM`, `REJECT`, `NEEDS_REVIEW`) recording human consensus without altering machine benchmarks or retraining models.

### Recruiter Walkthrough Mode
A guided 10-step tour through the complete lifecycle: problem, auto-clear, escalation, evidence graph, decision passport, fault injection, calibration drift, and benchmark validation.
