# SentinelLog Build Progress

## Project
SentinelLog — Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs

## Current Phase
Phase 3 — Unsupervised Anomaly Detection Baselines

## Status
COMPLETE (Phase 3 acceptance checks passed; awaiting human authorization to proceed to Phase 4)

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
- [x] Post-audit verified: Frozen vocabulary on train only, strict temporal timestamp inequality, and chronological subsampling.

## Completed (Phase 3)
- [x] Template count vectorizer with frozen training vocabulary and invariant UNKNOWN (-1) bin (`sentinellog/scoring/features.py`)
- [x] B0 Frequency Scorer baseline with smoothed mean negative log-frequency surprisal (`sentinellog/scoring/b0.py`)
- [x] B1 Primary: PCA reconstruction error anomaly detector with variance ratio component selection (`sentinellog/scoring/b1.py`)
- [x] B1 Secondary: Isolation Forest baseline with fixed random_state (`sentinellog/scoring/b1.py`)
- [x] Unsupervised calibration quantile thresholding and diagnostic evaluation with strict tied-score handling (`sentinellog/scoring/thresholds.py`)
- [x] Artifact management and programmatic Rule 1 test-access guard (`sentinellog/scoring/artifacts.py`)
- [x] Standalone baseline CLI runner and comparison reporting (`sentinellog/scoring/baselines.py`, `configs/baselines.yaml`)
- [x] Deterministic baseline experiment manifests, models, and diagnostics generated in `results/phase3/`
- [x] Unit and integration test suite with 14 comprehensive tests (`tests/test_baselines.py`)
- [x] Full test suite (41/41 tests passing) with clean compilation
- [x] Comprehensive baseline documentation (`docs/baselines.md`)

## Not Completed
- Phase 4 — Learned scorer (B2) and conformal risk calibration
- Phase 5 — Retrieval-augmented incident explanation and faithfulness checking
- Phase 6 — Full cascade integration and selective prediction triage
- Phase 7 — Frozen evaluation over benchmark test sets
- Phase 8 — Production service and API endpoint serving
- Phase 9 — Final deployment, containerization, and reproducibility artifacts

## Test Set
LOCKED (Rule 1)

## Test-set Access
FORBIDDEN until Phase 7.
(All Phase 3 baselines and threshold determinations were conducted exclusively on TRAIN and CALIBRATION. `test_used: false` verified across all manifests.)

## Last Validation
- Date: 2026-10-05
- Pytest: 41 passed in 22.54s (0 failed, 0 warnings)
- Syntax/Bytecode check: `python -m compileall -q sentinellog tests scripts` (Clean, exit code 0)
- Baseline Diagnostics on CALIBRATION (Unsupervised 95th percentile threshold):
  - HDFS B0 Frequency: Precision = 0.7308, Recall = 0.6552, F1 = 0.6909, ROC-AUC = 0.8501, PR-AUC = 0.6128
  - HDFS B1 PCA: Precision = 0.7308, Recall = 0.6552, F1 = 0.6909, ROC-AUC = 0.8237, PR-AUC = 0.5433
  - HDFS B1 Isolation Forest: Precision = 0.7308, Recall = 0.6552, F1 = 0.6909, ROC-AUC = 0.8221, PR-AUC = 0.4451
  - BGL B0 Frequency: Precision = 0.2000, Recall = 0.0278, F1 = 0.0488, ROC-AUC = 0.9089, PR-AUC = 0.7082
  - BGL B1 PCA: Precision = 0.2000, Recall = 0.0278, F1 = 0.0488, ROC-AUC = 0.2786, PR-AUC = 0.3679
  - BGL B1 Isolation Forest: Precision = 0.8000, Recall = 0.1111, F1 = 0.1951, ROC-AUC = 0.9390, PR-AUC = 0.8582
- Determinism Check: Running baseline pipeline multiple times produces identical scores, thresholds, and confusion matrices.
- Rule 1 Test Guard: Programmatically verified via `guard_no_test_split` regression tests.

## Next Authorized Phase
Phase 4 — Learned scorer (B2) and conformal risk calibration (PENDING HUMAN APPROVAL)
