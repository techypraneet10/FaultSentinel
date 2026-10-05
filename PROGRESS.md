# SentinelLog Build Progress

## Project
SentinelLog — Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs

## Current Phase
Phase 2 — Data Pipeline, Versioning & Leakage-Safe Dataset Construction

## Status
COMPLETE (Phase 2 acceptance checks passed; awaiting human authorization to proceed to Phase 3)

## Completed (Phase 1)
- [x] Repository inspection
- [x] Project skeleton structure
- [x] Python package scaffold
- [x] Dependency specification
- [x] Research-integrity guardrails (`AGENTS.md`)
- [x] Build and automation targets (`Makefile`)
- [x] Project ignore rules (`.gitignore`)
- [x] Setup verification tests (`tests/test_setup.py`)

## Completed (Phase 2)
- [x] Official Loghub HDFS dataset acquired from Zenodo (1.57 GB `HDFS.log`, 18.6 MB `anomaly_label.csv`, SHA-256 verified)
- [x] Official Loghub BGL dataset acquired from Zenodo (743 MB `BGL.log`, SHA-256 verified)
- [x] Raw data manifests generated (`data/raw/hdfs/manifest.json`, `data/raw/bgl/manifest.json`)
- [x] Drain3 streaming parser with regex masking and explicit `UNKNOWN` template handling (`sentinellog/ingestion/parser.py`)
- [x] HDFS session-based window construction (`sentinellog/ingestion/windowing.py`)
- [x] BGL fixed-size window construction with partial-window retention (`sentinellog/ingestion/windowing.py`)
- [x] Leakage-safe chronological splitting enforcing 60/20/20 partition and zero session/window ID overlap (`sentinellog/ingestion/splitter.py`)
- [x] Processed artifacts serialized as JSON Lines with provenance manifests (`data/processed/hdfs/`, `data/processed/bgl/`)
- [x] Machine-readable data quality reports generated (`data_quality_report.json`)
- [x] Comprehensive test suite covering leakage, unknown templates, and determinism (`tests/test_data_pipeline.py`)
- [x] All 26/26 tests passing, static compilation clean, zero leakage verified

## Not Completed
- Phase 3 — Unsupervised anomaly detection baselines (B0, B1)
- Phase 4 — Learned scorer (B2) and conformal risk calibration
- Phase 5 — Retrieval-augmented incident explanation and faithfulness checking
- Phase 6 — Full cascade integration and selective prediction triage
- Phase 7 — Frozen evaluation over benchmark test sets
- Phase 8 — Production service and API endpoint serving
- Phase 9 — Final deployment, containerization, and reproducibility artifacts

## Test Set
LOCKED

## Test-set Access
FORBIDDEN until Phase 7.
(Test partitions `data/processed/hdfs/test.jsonl` and `data/processed/bgl/test.jsonl` exist for structural verification only; no models or thresholds may touch them.)

## Last Validation
- Date: 2026-10-05
- Pytest: 27 passed in 11.19s (0 failed, 0 skipped)
- Syntax/Bytecode check: `python -m compileall -q sentinellog tests scripts` (Clean, exit code 0)
- Ingestion pipeline execution:
  - HDFS: 4,087 windows (Train: 2,450, Calib: 814, Test: 823). Strict timestamp boundary: max(train) = 1226243372.0 < min(calib) = 1226243373.0, max(calib) = 1226243457.0 < min(test) = 1226243458.0.
  - BGL: 500 windows (Train: 300, Calib: 100, Test: 100). Strict timestamp boundary: max(train) = 1117959468.0 < min(calib) = 1117959471.0, max(calib) = 1117973850.0 < min(test) = 1117973853.0.
- Template Vocabulary Integrity: Drain3 TemplateMiner fitted strictly on TRAIN sessions/windows only; vocabulary frozen before CALIBRATION and TEST parsing. Novel calibration/test templates map to UNKNOWN (-1) without altering learned clusters.
- Data Leakage Check: `leakage_check_passed = true` (Zero window ID overlap, zero session overlap, strict chronological boundaries).
- Determinism Check: Rerun produces 100% identical window IDs, counts, labels, and template sequences.

## Next Authorized Phase
Phase 3 — Unsupervised anomaly detection baselines (B0, B1) (PENDING HUMAN APPROVAL)
