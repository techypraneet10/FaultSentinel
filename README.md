# SentinelLog

Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs.

## Overview

SentinelLog investigates a cost-aware, reliability-calibrated cascade for automated incident triage over unstructured system logs:
- **Log Parsing**: Structural template extraction.
- **Anomaly Scoring**: Fast unsupervised anomaly scoring over parsed log windows.
- **Calibrated Selective Escalation**: Conformal prediction gating to selectively escalate high-uncertainty or ambiguous windows to expensive LLM reasoning under guaranteed coverage bounds.
- **Retrieval-Grounded Explanation**: Historical incident and runbook retrieval grounding.
- **Faithfulness Checking**: Self-contained verification of explanation claims against source log evidence.

## Current Status

**STATUS: Phase 2 — Data Pipeline, Versioning & Leakage-Safe Dataset Construction.**

> [!NOTE]
> Phase 2 data ingestion, Drain3 log parsing, session/fixed windowing, and leakage-safe chronological partitioning are complete.
> The test partitions (`data/processed/*/test.jsonl`) are strictly **FROZEN** and will not be accessed until Phase 7.
> No anomaly detection models (Phase 3) or calibrations (Phase 4) have been implemented yet.

## Development Principles

- **Leakage-Safe Evaluation**: Strict isolation between train, calibration, and test data.
- **Chronological Splits**: All temporal log data is partitioned chronologically; random shuffling of time-series log windows is strictly forbidden.
- **Frozen Test Set**: `data/test/` remains strictly locked and untouched until Phase 7 frozen evaluation.
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
pytest
```

### Run Data Ingestion Pipeline
```powershell
# Acquire official Loghub datasets (HDFS & BGL)
python scripts/acquire_data.py --dataset all

# Execute Drain3 parsing, windowing, and chronological splitting
python -m sentinellog.ingestion.pipeline --config configs/data_pipeline.yaml
```

### Lint / Static Validation
```powershell
python -m compileall -q sentinellog tests scripts
```
*(Or run `make setup`, `make test`, `make lint`, `make pipeline` on platforms where Make is installed.)*
