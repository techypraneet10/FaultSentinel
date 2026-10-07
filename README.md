# FaultSentinel

**AI-Assisted Incident Intelligence — Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis**
*(Formerly SentinelLog research prototype)*

## Overview

FaultSentinel investigates a cost-aware, reliability-calibrated cascade for automated incident triage over unstructured system logs:
- **Log Parsing**: Structural template extraction using Drain3 with regex masking and frozen training vocabulary.
- **Anomaly Scoring**: Fast classical baselines (B0 Frequency Rarity, B1 PCA Reconstruction, B1 Isolation Forest) and lightweight sequential modeling (B2 Sequential GRU).
- **Calibrated Selective Escalation**: Conformal prediction gating to selectively escalate high-uncertainty or ambiguous windows to expensive LLM reasoning under empirical risk control.
- **Retrieval-Grounded Explanation**: Historical incident and runbook retrieval grounding.
- **Faithfulness Checking**: Self-contained verification of explanation claims against source log evidence.

## Current Status

**STATUS: Phase 4 — Learned Sequential Scorer + Conformal Risk-Controlled Selective Gate COMPLETE.**

> [!NOTE]
> Phase 4 models (B2 Sequential GRU) and split conformal prediction gates have been trained and evaluated strictly on TRAIN and CALIBRATION.
> The test partitions (`data/processed/*/test.jsonl`) remain strictly **FROZEN** and will not be accessed until Phase 7.
> No Phase 5+ functionality (retrieval, vector databases, LLM calls, explanation generation) has been implemented yet.

## Development Principles

- **Leakage-Safe Evaluation**: Strict isolation between train, calibration, and test data.
- **Chronological Splits**: All temporal log data is partitioned chronologically; random shuffling of time-series log windows is strictly forbidden.
- **Frozen Test Set**: `data/test/` and `data/processed/*/test.jsonl` remain strictly locked and untouched until Phase 7 frozen evaluation.
- **Reproducibility**: All experiments require explicit seeds, configurations, dependency locks, and code provenance.
- **No Fabricated Results**: Unexecuted benchmarks are marked `NOT RUN / TBD`. No simulated or fabricated numbers are permitted.
- **Phase-Gated Development**: Strict sequential execution through authorized phases (Phases 1 through 9).

## Quickstart (Development Setup)

### Prerequisites
- Python 3.12 (recommended) or compatible 64-bit Python
- Virtual environment (`.venv`)

### Setup Environment
Using PowerShell on Windows:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run Tests
```powershell
.venv\Scripts\python.exe -m pytest -v tests
```

### Run Data Ingestion Pipeline (Phase 2)
```powershell
# Acquire official Loghub datasets (HDFS & BGL)
.venv\Scripts\python.exe scripts/acquire_data.py --dataset all

# Execute Drain3 parsing, windowing, and chronological splitting
.venv\Scripts\python.exe -m sentinellog.ingestion.pipeline --config configs/data_pipeline.yaml
```

### Run Baseline Anomaly Detectors (Phase 3)
```powershell
# Run B0, B1 PCA, and B1 Isolation Forest on HDFS and BGL
.venv\Scripts\python.exe -m sentinellog.scoring.baselines --config configs/baselines.yaml
```

### Run Learned Sequential Scorer & Conformal Selective Gate (Phase 4)
```powershell
# Run B2 Sequential GRU and Split Conformal Selective Gate across alpha grid
.venv\Scripts\python.exe -m sentinellog.scoring.phase4_runner --config configs/phase4.yaml
```
Results and diagnostic reports are serialized to `results/phase4/`.

### Lint / Static Validation
```powershell
.venv\Scripts\python.exe -m compileall -q sentinellog tests scripts
```
*(Or run `make setup`, `make test`, `make lint`, `make pipeline`, `make baselines`, `make phase4` on platforms where Make is installed.)*
