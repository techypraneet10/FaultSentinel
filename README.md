# FaultSentinel

### Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis

<p align="center">
  <strong>Detect cheaply. Escalate selectively. Reason deterministically. Preserve evidence.</strong>
</p>

<p align="center">
  FaultSentinel is an AI-assisted incident intelligence platform that detects anomalous system-log windows, selectively escalates high-risk events, retrieves historical evidence, performs deterministic incident reasoning, and generates evidence-grounded explanations.
</p>

<p align="center">

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Backend%20Tests-520%20passed-success?style=flat-square)](#testing)
[![Release](https://img.shields.io/badge/Release-v1.1.0-purple?style=flat-square)](#release)

</p>

---

## Why FaultSentinel?

Modern systems generate enormous volumes of logs, but detecting an unusual event is only the beginning of incident response.

An engineer still needs to answer:

> **What happened, why does the system believe it happened, and what evidence supports that conclusion?**

A naive LLM architecture sends every log window to an expensive language model:

```text
Millions of Log Windows
          │
          ▼
         LLM
          │
          ▼
 Expensive Investigation
```

That approach wastes inference budget on normal traffic and provides a weak foundation for calibrated, auditable decisions.

FaultSentinel takes a different approach:

```text
Cheap Detection
      ↓
Risk Calibration
      ↓
Selective Escalation
      ↓
Historical Evidence
      ↓
Deterministic Reasoning
      ↓
LLM Explanation
      ↓
Faithfulness Validation
      ↓
Auditable Incident Result
```

The LLM is **not the detector of record**.

It is a downstream explanation component operating after the system has established a decision boundary, selected evidence, verified provenance, and performed deterministic reasoning.

---

## Core Idea

> **Do not send every log window to an expensive LLM.**

FaultSentinel separates the system into explicit decision stages:

```text
Raw Logs
   │
   ▼
Drain3 Parsing
   │
   ▼
Window Construction
   │
   ▼
Anomaly Detection
   │
   ▼
Conformal Risk-Controlled Gate
   │
   ├───────────────► AUTO-CLEAR
   │
   ▼
ESCALATE
   │
   ▼
Historical Retrieval
   │
   ▼
Evidence Selection / MMR
   │
   ▼
Provenance Verification
   │
   ▼
Deterministic Reasoning
   │
   ▼
LLM Explanation
   │
   ▼
Faithfulness Validation
   │
   ▼
Auditable Incident Result
```

This architecture creates a clean separation between:

| Layer | Responsibility |
|---|---|
| Detection | Identify anomalous log behavior |
| Calibration | Establish a controlled escalation boundary |
| Selective Gate | Decide which windows require expensive investigation |
| Retrieval | Find relevant historical evidence |
| Evidence Selection | Reduce redundancy and improve evidence quality |
| Provenance | Verify that evidence corresponds to authoritative source material |
| Reasoning | Produce the authoritative machine decision |
| LLM | Explain the already-established decision |
| Validation | Check generated claims against evidence |
| Audit | Preserve the decision, evidence, hashes, and execution context |

---

## Key Results

FaultSentinel is deliberately evaluated without hiding negative or neutral results.

The frozen HDFS evaluation contains **823 windows**.

### Frozen HDFS Detection Result

| Metric | FaultSentinel | B2 |
|---|---:|---:|
| True Positives | 12 | 12 |
| False Positives | 31 | 31 |
| True Negatives | 762 | 762 |
| False Negatives | 18 | 18 |
| Precision | 27.91% | 27.91% |
| Recall | 40.00% | 40.00% |
| F1 | 32.88% | 32.88% |
| FPR | 3.91% | 3.91% |

The corrected McNemar comparison reports:

```text
b = 400
c = 31
χ² ≈ 314.21
p ≈ 2.64 × 10⁻⁷⁰
```

### What This Means

**FaultSentinel does not claim that adding the LLM pipeline improves raw binary anomaly-detection performance over B2.**

The frozen detection metrics are identical.

The engineering contribution is instead the layer that comes **after scoring**:

- calibrated selective escalation
- reduced expensive downstream investigation
- historical evidence retrieval
- evidence selection
- provenance verification
- deterministic reasoning
- citation traceability
- faithfulness validation
- incident replay
- reliability testing
- decision auditability

### Selective Escalation Result

At the evaluated HDFS configuration:

| Measurement | Result |
|---|---:|
| Calibration threshold | **1.1546** |
| Target α | **0.05** |
| Escalation coverage | **5.22%** |
| LLM calls | **43 / 823** |
| Expensive-call reduction | **94.78%** |
| Escalated precision | **27.91%** |
| Recall | **40.00%** |

The important systems result is therefore:

> **Only 43 of 823 windows required the expensive downstream explanation path.**

The selective gate is a **cost-control and investigation-routing mechanism**, not evidence that the underlying detector became more accurate.

---

## System Architecture

```text
                         ┌──────────────────────┐
                         │    Raw System Logs   │
                         │      Loghub Data     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       Drain3         │
                         │   Template Parsing   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Window Construction │
                         │ Chronological Events │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Anomaly Detection   │
                         │      B1 / B2         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Conformal Calibration│
                         │    Risk-Controlled   │
                         │        Gate          │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
                  ┌─────────────┐       ┌─────────────┐
                  │ AUTO-CLEAR  │       │   ESCALATE  │
                  └─────────────┘       └──────┬──────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │    Retrieval    │
                                      │ Historical Logs │
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Evidence Select │
                                      │      / MMR      │
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │   Provenance    │
                                      │   Verification  │
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Deterministic   │
                                      │    Reasoning    │
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │  LLM Explanation│
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │   Faithfulness  │
                                      │    Validation   │
                                      └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Auditable Result│
                                      └─────────────────┘
```

---

## End-to-End Pipeline

### 1. Log Parsing

Raw log messages are converted into structured templates using **Drain3**.

The parser separates stable log structure from variable parameters, producing template-oriented events suitable for downstream sequence modeling.

This provides a common representation for heterogeneous raw logs.

---

### 2. Window Construction

Parsed events are organized into chronological log windows.

The evaluation pipeline uses dataset-specific construction:

- session-oriented windows for HDFS
- fixed/sliding windows for BGL
- chronological ordering
- explicit handling of unknown templates

The objective is to preserve operational sequence information without allowing future information to leak into earlier decisions.

---

### 3. Anomaly Detection

FaultSentinel supports multiple detection baselines.

#### B0 — Frequency / Rule Baseline

A lightweight baseline based on frequency/rule signals.

#### B1 — Statistical Baseline

Drain3-derived representations combined with lightweight statistical anomaly detection.

#### B2 — Sequence Model

A recurrent sequence-based anomaly scorer.

The current replay implementation uses a **B2 GRU-based scorer** with a compact PyTorch model.

#### B3 — LLM-Every-Window

A comparison architecture where every window is sent to an LLM.

This establishes the cost/calibration contrast against the selective architecture.

---

## Calibrated Selective Escalation

The central decision is not:

> "Is the LLM confident?"

It is:

> **"Does this window require expensive downstream investigation?"**

The system uses a conformal calibration layer to establish an escalation boundary.

For the HDFS α=0.05 configuration:

```text
Anomaly Score
      │
      ▼
Conformal Gate
      │
      ├── below threshold ──► AUTO-CLEAR
      │
      └── above threshold ──► ESCALATE
```

The calibrated HDFS threshold used by the current implementation is approximately:

```text
1.1546
```

The calibration monitor is intentionally **observational**.

It does not automatically:

- recalibrate
- change α
- retune thresholds
- mutate frozen calibration artifacts

Human review is required before creating and validating a new calibration artifact.

---

## Historical Evidence Retrieval

Escalated windows are enriched with historical evidence.

The retrieval layer operates against a **training-only evidence corpus** during evaluation to reduce test leakage.

The objective is not simply to retrieve text that looks similar.

The retrieved material becomes evidence that must pass subsequent provenance and reasoning checks.

---

## Evidence Selection

Retrieved candidates are reduced through relevance/diversity selection.

FaultSentinel uses an MMR-style reranking stage to avoid returning multiple near-duplicate pieces of evidence.

Conceptually:

```text
Retrieved Candidates
        │
        ├── relevance
        │
        ├── similarity
        │
        └── diversity
               │
               ▼
       Selected Evidence
```

This creates a smaller evidence set for deterministic reasoning and the downstream explanation model.

---

## Provenance

Evidence is not treated as trustworthy simply because a retriever returned it.

FaultSentinel maintains provenance information connecting:

```text
Incident
   ↓
Window
   ↓
Anomaly Signal
   ↓
Decision
   ↓
Retrieved Evidence
   ↓
Citation
   ↓
Source Log
```

The provenance layer verifies source integrity before downstream reasoning and explanation.

The replay implementation includes a dual-hash provenance gate and fails closed when integrity verification fails.

---

## Deterministic Reasoning

The authoritative incident decision is produced by a deterministic reasoning engine rather than delegated to the LLM.

The reasoning layer performs:

1. input validation
2. label-leakage checks
3. provenance verification
4. signal extraction
5. evidence contribution evaluation
6. conflict detection
7. rule-precedence evaluation
8. severity determination
9. deterministic confidence calculation
10. machine-readable reasoning trace generation

The resulting assessment contains structured decision, severity, confidence, evidence, provenance status, engine version, and configuration hash information.

The LLM therefore does **not** get to silently change the authoritative decision.

---

## LLM Explanation

The LLM is used as a **grounded technical explainer**.

The explanation pipeline:

```text
Authoritative Decision
        +
Verified Evidence
        +
Reasoning Trace
        │
        ▼
Bounded Context
        │
        ▼
Injection-Resistant Prompt
        │
        ▼
LLM
        │
        ▼
Structured Explanation
        │
        ▼
Validation
```

The implementation includes:

- bounded context construction
- split protection
- label-leakage protection
- provenance gating
- retry controls
- timeout controls
- deterministic temperature configuration
- structured explanation output
- fallback handling
- decision immutability

If provenance is invalid, the explanation stage abstains instead of calling the LLM.

If the provider fails or times out, FaultSentinel can return a deterministic fallback rather than failing the entire investigation.

---

## Faithfulness Validation

FaultSentinel validates generated explanations against the evidence and citation register.

This is **grounding validation**, not a claim of hallucination-free generation.

A successful explanation should have claims that can be traced back to verified evidence.

If validation fails, the system can reject the generated explanation and use a fallback/abstention path.

---

# v1.1 Investigation & Reliability Workbench

FaultSentinel v1.1 adds a dedicated investigation and reliability workbench.

## Incident Replay Lab

The replay engine reconstructs the incident pipeline as an **11-stage execution trace**:

```text
01  INGEST
02  PARSE
03  WINDOW
04  SCORE
05  CONFORMAL
06  RETRIEVE
07  MMR
08  PROVENANCE
09  REASONING
10  LLM
11  VERIFY
```

The frontend provides controls for:

- first
- previous
- play
- pause
- next
- last
- 0.5×
- 1×
- 2×

It also exposes:

- stage inspection
- analytical synthesis
- counterfactual decision analysis

The purpose is to make the entire AI decision path inspectable rather than presenting only a final answer.

---

## Reliability & Fault Injection Lab

FaultSentinel includes controlled, non-destructive reliability scenarios.

Supported scenarios include:

| Scenario | Purpose |
|---|---|
| `llm_unavailable` | Verify safe LLM failure handling |
| `retrieval_unavailable` | Verify insufficient-evidence behavior |
| `invalid_log_input` | Test ingestion validation |
| `parser_failure` | Test malformed payload handling |
| `faithfulness_failure` | Verify failed grounding is rejected |
| `invalid_auth` | Verify authentication enforcement |
| `invalid_authz` | Verify role authorization |
| `config_failure` | Verify fail-closed production configuration |
| `timeout_simulation` | Test bounded timeout behavior |

Fault injection is explicitly disabled in production:

```text
DISABLED_IN_PRODUCTION
```

The scenarios are designed to verify graceful degradation, fail-closed behavior, and safety boundaries.

---

## Calibration Drift Monitor

The calibration monitor tracks changes in:

- Population Stability Index (PSI)
- score quantiles
- empirical escalation rate
- score mean
- score standard deviation
- distribution shifts
- sample sufficiency

Operational states include:

```text
STABLE
WATCH
DRIFT DETECTED
INSUFFICIENT DATA
```

### Important Safety Property

The drift monitor **does not automatically recalibrate the system**.

A review workflow is required before a new calibration artifact is produced, versioned, benchmarked, and approved.

---

## Evidence Graph & Provenance DAG

FaultSentinel exposes an evidence/provenance graph connecting the major objects involved in an incident:

```text
Incident
   │
   ▼
Window
   │
   ▼
Score
   │
   ▼
Decision
   │
   ▼
Retrieved Chunk
   │
   ▼
Evidence
   │
   ▼
Provenance
   │
   ├──────────────► Citation
   │
   ▼
Reasoning Claim
   │
   ▼
LLM Claim
   │
   ▼
Source Log
```

The graph represents **11 node types**:

1. Incident
2. Window
3. Score
4. Decision
5. Retrieved Chunk
6. Evidence
7. Provenance
8. Citation
9. Reasoning Claim
10. LLM Claim
11. Source Log

Unresolved relationships are explicitly represented rather than fabricated.

---

## Decision Passport

Every investigated decision can be represented as a cryptographically auditable **Decision Passport**.

The passport records information including:

- FaultSentinel version
- pipeline version
- incident ID
- dataset
- window ID
- timestamp
- anomaly score
- calibration α
- threshold
- conformal decision
- final decision
- severity
- escalation state
- retrieval count
- selected evidence count
- citation count
- faithfulness status
- LLM invocation state
- Git commit
- configuration hash
- evidence hash
- decision hash
- generation timestamp

The decision hash binds the incident decision to its relevant configuration, evidence, and Git revision.

Passports can be exported as structured JSON and rendered as Markdown reports.

They can also be cryptographically verified.

---

## Human Adjudication

FaultSentinel supports explicit human review states:

```text
CONFIRM
REJECT
NEEDS_REVIEW
```

Review records can include:

- incident ID
- machine decision
- human decision
- rejection reason
- reviewer notes
- reviewer ID
- timestamp

Human feedback is deliberately separated from scientific evaluation.

> **Human adjudication does not automatically retrain models, mutate calibration, or alter frozen benchmark results.**

This prevents operational feedback from silently contaminating benchmark evaluation.

---

## Recruiter Tour Mode

FaultSentinel includes a guided walkthrough designed to demonstrate the system's engineering depth.

Rather than requiring a recruiter to understand the entire repository first, the tour exposes the major concepts:

```text
Detection
   ↓
Calibration
   ↓
Escalation
   ↓
Retrieval
   ↓
Evidence
   ↓
Provenance
   ↓
Reasoning
   ↓
Explanation
   ↓
Verification
   ↓
Audit
```

The goal is to make the project's architecture understandable through the actual product interface.

---

# Research Question

FaultSentinel investigates a specific systems question:

> **Can calibrated selective escalation reduce expensive downstream LLM investigation while preserving a controlled decision policy, compared with sending every log window to an LLM?**

The project evaluates this against:

- classical anomaly detection
- sequence-based anomaly detection
- fixed-threshold escalation
- conformal selective escalation
- LLM-every-window analysis
- retrieval-enabled versus retrieval-disabled configurations

The project is positioned as an **engineering-research system and empirical study**, not as a claim of a new conformal prediction algorithm.

---

# Detection Baselines

| Baseline | Description | Purpose |
|---|---|---|
| **B0** | Frequency/rule baseline | Establish a simple non-ML reference |
| **B1** | Drain3 + statistical anomaly detection | Evaluate lightweight structured-log detection |
| **B2** | GRU/LSTM sequence model | Capture sequential log behavior |
| **B3** | LLM on every window | Measure naive LLM-based investigation cost |
| **FaultSentinel** | B1/B2 → calibration → selective escalation → retrieval → reasoning → LLM → validation | Evaluate the complete architecture |

The baselines are important because FaultSentinel is not evaluated against a strawman.

---

# Datasets

FaultSentinel is evaluated using public Loghub datasets.

## HDFS

```text
Messages:        11,175,629
Block sessions:  16,838
Anomaly rate:    ~2.93%
```

## BGL

```text
Messages:        4,747,963
Anomaly rate:    ~7.41%
```

Development experiments use the first **50,000 contiguous records**.

### BGL Evaluation Note

The evaluated BGL safety slice contains **no positive incidents**.

Observed:

```text
False positives = 0
LLM calls       = 0
```

Therefore:

> Positive-class recall and F1 are **not meaningful** for this slice.

This result is reported as a safety-slice observation, not as evidence of positive-class detection performance.

---

# Evaluation Methodology

The evaluation pipeline emphasizes leakage resistance and reproducibility.

### Dataset Controls

- chronological splitting
- train/calibration/test separation
- frozen test set
- no random test shuffling
- no synthetic anomalies in frozen evaluation
- explicit unknown-template handling
- training-only retrieval evidence
- versioned artifacts
- reproducibility metadata

### Evaluation Structure

```text
Raw Dataset
    │
    ▼
Chronological Split
    │
    ├── Train
    │     └── Detector / Retrieval
    │
    ├── Calibration
    │     └── Conformal Threshold
    │
    └── Frozen Test
          └── One-time Evaluation
```

The frozen test set is kept separate from downstream explanation generation and operational review.

---

# Evaluation Results

## HDFS

The frozen HDFS result shows that the proposed cascade did **not** improve binary detection metrics over B2.

```text
                     FaultSentinel     B2
------------------------------------------------
Precision                 27.91%       27.91%
Recall                    40.00%       40.00%
F1                        32.88%       32.88%
False Positive Rate        3.91%        3.91%
```

The value of the architecture is therefore not a claimed improvement in the underlying classifier.

It is the controlled routing of downstream investigation.

### Selective Investigation

```text
Test windows:             823
LLM calls:                 43
Escalation coverage:       5.22%
Expensive-call reduction: 94.78%
Target alpha:              0.05
Threshold:                 1.1546
```

This demonstrates the intended cascade behavior:

```text
823 windows
    │
    ├── 780 approximately remain on the cheap path
    │
    └── 43 enter expensive downstream investigation
```

---

# What the Results Mean

The strongest claim FaultSentinel can make from the frozen evaluation is:

> **The architecture provides a selective investigation mechanism that dramatically reduces the number of expensive LLM calls while preserving the measured B2 binary detection behavior on the frozen HDFS slice.**

The project does **not** claim:

- state-of-the-art anomaly detection
- improved binary anomaly detection from LLM usage
- hallucination-free explanations
- universally reliable root-cause diagnosis
- production-scale operational guarantees
- automatic remediation

This distinction is intentional.

---

# Example Incident

A representative escalated incident follows this path:

```text
Raw Log Window
      │
      ▼
Drain3 Template Extraction
      │
      ▼
B2 Sequential Anomaly Score
      │
      ▼
Score > Conformal Threshold
      │
      ▼
ESCALATE
      │
      ▼
Retrieve Historical Incidents
      │
      ▼
MMR Evidence Selection
      │
      ▼
Dual-Hash Provenance Verification
      │
      ▼
Deterministic Reasoning
      │
      ▼
Grounded LLM Explanation
      │
      ▼
Programmatic Faithfulness Check
      │
      ▼
Decision Passport
```

A normal window follows the much shorter path:

```text
Raw Log
  ↓
Parse
  ↓
Window
  ↓
Score
  ↓
Conformal Gate
  ↓
AUTO-CLEAR
```

The expensive stages are therefore not executed for every window.

---

# Production-Oriented Architecture

FaultSentinel is structured as a service-oriented application rather than only a research notebook.

```text
                    ┌──────────────────────┐
                    │   React Dashboard    │
                    │   TypeScript / Vite  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │    Serving Layer     │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        Detection        Investigation     Observability
              │                │                │
              ▼                ▼                ▼
        Calibration       Retrieval        Metrics
              │                │            Logging
              ▼                ▼            Tracing
        Selective Gate    Provenance        Diagnostics
              │                │
              ▼                ▼
        Reasoning          Explanation
              │                │
              └────────┬───────┘
                       ▼
                 Incident Result
```

The backend application is exposed through FastAPI and includes middleware for security hardening, observability, request correlation, and centralized exception handling.

---

# Technology Stack

The implementation uses the following core technologies.

### Backend

- **Python 3.12**
- **FastAPI**
- **Uvicorn**
- **Pydantic**
- **NumPy**
- **Pandas**
- **scikit-learn**
- **PyTorch**
- **Drain3**
- **sentence-transformers**
- **PyYAML**

### Frontend

- **React 18**
- **TypeScript**
- **Vite**
- **Lucide React**
- **Vitest**
- React Testing Library
- ESLint

### Runtime

- Docker
- Python slim runtime image
- Uvicorn / ASGI

The dependency set is explicitly pinned in `requirements.txt` and `frontend/package.json`.

---

# Project Structure

The repository is organized around the incident-intelligence pipeline rather than a single monolithic application.

```text
FaultSentinel/
│
├── sentinellog/
│   ├── ingestion/
│   │   ├── log readers
│   │   ├── Drain3 parsing
│   │   └── window construction
│   │
│   ├── scoring/
│   │   ├── anomaly scoring
│   │   └── B2 sequence model
│   │
│   ├── calibration/
│   │   └── conformal selective gate
│   │
│   ├── retrieval/
│   │   └── historical evidence retrieval
│   │
│   ├── provenance/
│   │   └── citation and source verification
│   │
│   ├── reasoning/
│   │   ├── signal aggregation
│   │   ├── rule engine
│   │   ├── confidence
│   │   └── reasoning traces
│   │
│   ├── explanation/
│   │   ├── context construction
│   │   ├── LLM client
│   │   ├── prompt orchestration
│   │   ├── validation
│   │   └── fallback handling
│   │
│   ├── workbench/
│   │   ├── replay
│   │   ├── fault injection
│   │   ├── calibration drift
│   │   ├── evidence graph
│   │   ├── decision passport
│   │   └── human adjudication
│   │
│   ├── serving/
│   │   ├── FastAPI application
│   │   ├── API routes
│   │   ├── schemas
│   │   └── services
│   │
│   ├── observability/
│   │   ├── structured logging
│   │   ├── metrics
│   │   ├── tracing
│   │   └── diagnostics
│   │
│   ├── security/
│   │   ├── authentication
│   │   ├── authorization
│   │   ├── rate limiting
│   │   └── security middleware
│   │
│   └── deployment/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── components/
│   └── package.json
│
├── tests/
├── results/
├── configs/
├── data/
├── docs/
├── scripts/
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

# API

The FastAPI application exposes OpenAPI documentation through:

```text
http://localhost:8000/docs
```

and ReDoc through:

```text
http://localhost:8000/redoc
```

## Core API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1` | Service/API metadata |
| `POST` | `/api/v1/analyze` | Analyze a bounded log sequence |

## Health & Observability

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/observability` | Telemetry health |
| `GET` | `/metrics` | Prometheus-format metrics |
| `GET` | `/api/v1/diagnostics` | Safe runtime diagnostics |

## Investigation Workbench

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/replay/{incident_id}` | Retrieve incident replay |
| `GET` | `/api/v1/replay/sample/{scenario_type}` | Retrieve sample replay |
| `POST` | `/api/v1/incidents/counterfactual` | Run score counterfactual |
| `GET` | `/api/v1/calibration/drift` | Evaluate calibration drift |
| `GET` | `/api/v1/evidence/{incident_id}/graph` | Retrieve evidence graph |
| `GET` | `/api/v1/incidents/{incident_id}/passport` | Generate Decision Passport |
| `POST` | `/api/v1/incidents/{incident_id}/passport/verify` | Verify Decision Passport |
| `POST` | `/api/v1/incidents/{incident_id}/review` | Record human adjudication |
| `GET` | `/api/v1/incidents/{incident_id}/reviews` | Retrieve incident reviews |
| `GET` | `/api/v1/incidents/reviews/summary` | Aggregate review summary |

## Reliability Lab

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/fault-injection/scenarios` | List supported scenarios |
| `POST` | `/api/v1/fault-injection/run` | Execute a controlled scenario |

---

# Frontend

The React dashboard is organized around operational investigation rather than a generic chatbot interface.

Current application areas include:

- Analyze
- Overview
- Incidents
- Anomaly Explorer
- Evaluation Lab
- Cost Intelligence
- Model Observatory
- Architecture
- API Status
- Human Review
- Incident Replay
- Fault Injection
- Calibration Health
- Evidence Graph
- Decision Passport
- Recruiter Walkthrough

The dashboard supports switching between HDFS and BGL datasets and includes a demo mode for controlled exploration.

---

# Quick Start

## 1. Clone

```bash
git clone https://github.com/techypraneet10/FaultSentinel.git
cd FaultSentinel
```

## 2. Create Python Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment

### Windows

```powershell
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Review the environment configuration before starting the service.

**Never commit real credentials or API keys.**

## 5. Start the Backend

```bash
python -m uvicorn sentinellog.serving.app:app --host 127.0.0.1 --port 8000
```

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

## 6. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

The frontend can be configured with:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

# Local Development

### Backend

```bash
python -m uvicorn sentinellog.serving.app:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Frontend Checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

---

# Docker

FaultSentinel includes a hardened multi-stage Docker build.

The container:

- uses Python 3.12 slim
- separates build and runtime stages
- runs as an unprivileged UID/GID `10001`
- avoids baking secrets into the image
- exposes port `8000`
- includes a liveness health check
- supports read-only-root-compatible operation
- enables production security settings through environment configuration

Build:

```bash
docker build -t faultsentinel .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env faultsentinel
```

The container starts:

```text
uvicorn sentinellog.serving.app:app
```

and exposes:

```text
http://localhost:8000
```

---

# Testing

FaultSentinel maintains separate backend, feature-workbench, and frontend validation.

## Current Validated Results

| Area | Result |
|---|---:|
| Backend test suite | **520 passed** |
| Backend warnings | **1 warning** |
| v1.1 feature suite | **70 passed** |
| Frontend tests | **50 / 50 passed** |
| Production frontend build | **1,956 modules transformed** |
| JavaScript bundle | **361.30 kB** |
| Gzip bundle | **92.98 kB** |
| Secret scan | **PASS** |

No code-coverage percentage is claimed.

The single backend warning is intentionally not hidden.

---

# Observability

FaultSentinel treats observability as part of the application rather than an afterthought.

## Structured Logging

Requests and pipeline events can be emitted through structured logging with request correlation.

## Metrics

The backend exposes Prometheus-compatible metrics including measurements for:

- HTTP requests
- request errors
- request latency
- analysis count
- analysis latency
- ingestion
- scoring
- auto-clears
- escalations
- escalation rate
- retrieval
- reranking
- provenance verification
- reasoning
- decisions
- explanations
- faithfulness
- authentication failures
- authorization denials
- rate-limit violations
- LLM requests
- LLM failures
- LLM latency
- per-stage latency

Metric labels are deliberately bounded to avoid uncontrolled cardinality.

## Health Probes

```text
/health/live
/health/ready
/health/observability
```

## Runtime Diagnostics

```text
/api/v1/diagnostics
```

The diagnostics endpoint is designed to expose bounded operational information without exposing secrets or raw internal paths.

These telemetry mechanisms are **observability features**, not guarantees of a production SLO.

---

# Security

FaultSentinel includes defense-in-depth controls around the serving layer.

### Authentication

Protected API access can require API-key or Bearer-token credentials.

### Authorization

Requests are mapped to roles and unauthorized endpoint access is rejected.

### Rate Limiting

Configurable request-rate limiting protects the API from uncontrolled request volume.

### Request Bounds

Payload size limits are enforced before request processing.

### Input Validation

Pydantic schemas validate API payloads at the application boundary.

### CORS

Allowed origins are explicitly configured.

Wildcard CORS is rejected in hardened production mode.

### Security Headers

The service sets headers including:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Content-Security-Policy: ...
```

HSTS is applied when requests are served over HTTPS.

### Secrets

Environment configuration is used for credentials.

`.env` files are ignored by Git while `.env.example` remains available as a safe configuration template.

---

# Reproducibility

FaultSentinel treats reproducibility as a first-class engineering requirement.

The evaluation workflow incorporates:

- pinned raw dataset hashes
- versioned processed artifacts
- chronological splits
- frozen test evaluation
- explicit test-leakage prevention
- no synthetic anomalies in frozen evaluation
- unknown-template handling
- training-only retrieval
- experiment manifests
- Git SHA tracking
- configuration hashes
- evidence hashes
- decision hashes

The reasoning engine also computes deterministic configuration fingerprints, allowing a decision to be tied to the configuration under which it was produced.

The Decision Passport extends this principle to the incident level.

---

# Deployment Architecture

FaultSentinel is packaged as a containerized FastAPI service and is structured to support deployment beyond local development.

The repository should distinguish between:

### Deployment Architecture

Infrastructure definitions and container configuration describe **how the system could be deployed**.

### Live Production Deployment

Infrastructure configuration alone does **not** prove that the system is currently operating as a live production service.

Accordingly, this README does not claim live AWS production deployment or production SLO compliance without corresponding operational evidence.

---

# Release

Current application release:

```text
v1.1.0
```

The v1.1 release extends the core triage pipeline with an investigation and reliability workbench:

```text
Core Triage
    +
Incident Replay
    +
Fault Injection
    +
Calibration Drift
    +
Evidence Graph
    +
Decision Passport
    +
Human Adjudication
    +
Recruiter Tour
```

---

# Engineering Validation

FaultSentinel has been designed around several engineering properties that matter beyond model accuracy.

### Decision Immutability

The LLM explanation layer consumes the authoritative deterministic decision rather than replacing it.

### Provenance Gating

Invalid evidence provenance prevents downstream explanation generation.

### Fail-Closed Validation

Unsupported or ungrounded outputs can be rejected instead of silently accepted.

### Graceful Degradation

LLM/provider failures can fall back to deterministic explanations rather than bringing down the entire triage operation.

### Production Fault-Injection Guard

Reliability simulations are explicitly disabled in production environments.

### Scientific Isolation

Human adjudication does not automatically alter model behavior or frozen benchmark artifacts.

### Calibration Safety

Drift monitoring is observational; it does not silently recalibrate the system.

### Auditability

Decision Passports bind important execution information to cryptographic hashes and Git provenance.

---

# Limitations

FaultSentinel intentionally documents where the system's evidence stops.

## 1. Temporal Exchangeability

Conformal risk-control guarantees rely on assumptions that are imperfect for temporally correlated, bursty operational logs.

The project therefore treats empirical calibration behavior as something to measure rather than assume away.

## 2. Grounding Is Not Hallucination-Proofing

Faithfulness validation verifies grounding against available evidence.

It is **not proof that an LLM can never hallucinate**.

## 3. Retrieval Overlap

The retrieval corpus is derived from Loghub-related material, which introduces potential circularity concerns when evaluating evidence-grounded explanations on the same benchmark family.

## 4. Benchmark Realism

HDFS and BGL are established public benchmarks, but they do not fully represent modern cloud-native microservice environments.

## 5. Binary Detection

The proposed pipeline did not improve the frozen HDFS binary detection metrics over B2.

That is a measured result, not something hidden by the README.

## 6. BGL Safety Slice

The evaluated BGL slice contains no positive incidents.

Therefore positive-class recall and F1 cannot meaningfully be interpreted for that slice.

## 7. Production Deployment

Infrastructure/container readiness does not constitute evidence of live production deployment.

## 8. Distributed Operations

Distributed rate limiting, multi-region disaster recovery, and large-scale operational validation require separate live-system validation.

---

# What FaultSentinel Does Not Attempt

FaultSentinel intentionally does not attempt to:

- automatically restart services
- automatically roll back deployments
- perform autonomous remediation
- guarantee zero hallucinations
- guarantee root-cause correctness
- replace human SRE judgment
- solve arbitrary zero-day failure modes
- perform distributed-trace causal analysis
- fine-tune a large foundation model

The system is an **incident intelligence and investigation layer**, not an autonomous remediation agent.

---

# Design Principles

FaultSentinel follows eight engineering principles:

> **Detect cheaply.**  
> **Escalate selectively.**  
> **Reason deterministically.**  
> **Ground explanations.**  
> **Preserve provenance.**  
> **Measure instead of assuming.**  
> **Fail visibly.**  
> **Document limitations.**

These principles drive both the architecture and the evaluation methodology.

---

# Future Research

The following are intentionally future directions rather than claims of completed functionality:

- larger production-like datasets
- cross-dataset generalization
- cloud-native log benchmarks
- temporal conformal methods
- online calibration research
- deeper retrieval ablations
- larger-scale latency/cost experiments
- human evaluation of explanation usefulness
- distributed rate limiting
- multi-region disaster recovery
- broader operational deployment validation

---

# Why This Project Is Technically Interesting

FaultSentinel is not primarily interesting because it calls an LLM.

The engineering challenge is the **system around the LLM**.

It combines:

```text
Sequence Anomaly Detection
          +
Statistical Calibration
          +
Selective Prediction
          +
Historical Retrieval
          +
Evidence Selection
          +
Provenance
          +
Deterministic Reasoning
          +
LLM Orchestration
          +
Faithfulness Validation
          +
Reliability Engineering
          +
Observability
          +
Security
          +
Reproducibility
```

The resulting system treats an AI-generated explanation as one component of an auditable decision pipeline rather than as the decision itself.

---

# Author

**Praneet**

B.Tech — Artificial Intelligence & Data Science

Areas of interest:

- Artificial Intelligence
- Machine Learning
- Generative AI
- LLM Systems
- Retrieval-Augmented Generation
- Agentic AI
- Data Engineering
- Reliable AI
- Production ML Systems

---

# License

See the repository's license configuration for the authoritative licensing terms.

---

<p align="center">
  <strong>FaultSentinel</strong><br/>
  Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis
</p>

<p align="center">
  <sub>AI should not only produce an answer. It should make the path to that answer inspectable.</sub>
</p>
