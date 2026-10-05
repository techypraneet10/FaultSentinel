# SentinelLog Build Progress

## Project
SentinelLog — Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs

## Current Phase
Phase 4 — Learned Sequential Scorer + Conformal Risk-Controlled Selective Gate

## Status
COMPLETE (Phase 4 acceptance checks passed; awaiting human authorization to proceed to Phase 5)

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
- [x] Unit and integration test suite with 15 comprehensive tests (`tests/test_baselines.py`)
- [x] Full test suite (42/42 tests passing) with clean compilation
- [x] Comprehensive baseline documentation (`docs/baselines.md`)

## Completed (Phase 4)
- [x] Sequence tokenizer with frozen TRAIN vocabulary, explicit PAD (0) and UNKNOWN (1) tokens (`sentinellog/scoring/tokenizer.py`)
- [x] Lightweight PyTorch Sequential GRU model (< 2,000,000 parameters, actual ~20.5K params) (`sentinellog/scoring/b2_model.py`)
- [x] Autoregressive next-template training loop with normal-only filtering and internal chronological 90/10 early stopping (`sentinellog/scoring/b2.py`)
- [x] Sequence nonconformity score based on mean negative log-likelihood of observed transitions (`sentinellog/scoring/b2.py`)
- [x] Finite-sample split conformal calibrator with exact order-statistic quantiles and p-values (`sentinellog/calibration/conformal.py`)
- [x] Selective escalation gate (`AUTO-CLEAR` vs `ESCALATE`) and risk-coverage metrics (`sentinellog/calibration/gate.py`)
- [x] Target alpha sweep ($\alpha \in \{0.01, 0.05, 0.10, 0.20\}$) evaluating coverage, selective risk, and empirical miscoverage
- [x] Comprehensive ablations: Heuristic threshold vs Conformal (Ablation A), B1 PCA vs B2 GRU (Ablation B), Calibration sample size sensitivity (Ablation C)
- [x] Standalone Phase 4 CLI runner and report generator (`sentinellog/scoring/phase4_runner.py`, `configs/phase4.yaml`)
- [x] Phase 4 unit and integration test suite with 16 comprehensive tests (`tests/test_phase4.py`)
- [x] Complete test suite passing (58/58 tests passing in 34s) on Python 3.12.4 CPU `.venv`
- [x] Comprehensive Phase 4 documentation (`docs/phase4.md`)

## Not Completed
- Phase 5 — Retrieval-augmented incident explanation and faithfulness checking
- Phase 6 — Full cascade integration and selective prediction triage
- Phase 7 — Frozen evaluation over benchmark test sets
- Phase 8 — Production service and API endpoint serving
- Phase 9 — Final deployment, containerization, and reproducibility artifacts

## Test Set
LOCKED (Rule 1)

## Test-set Access
FORBIDDEN until Phase 7.
(All Phase 4 models, tokenizers, internal validation, and conformal calibrations were conducted exclusively on TRAIN and CALIBRATION. `test_used: false` verified across all manifests.)

## Last Validation
- Date: 2026-10-05
- Pytest: 58 passed in 33.96s (0 failed, 0 warnings)
- Syntax/Bytecode check: `.venv\Scripts\python.exe -m compileall -q sentinellog tests scripts` (Clean, exit code 0)
- B2 GRU Parameter Count: HDFS = 20,562 params; BGL = 20,853 params (strictly < 2,000,000)
- Conformal Selective Gate Diagnostics (CALIBRATION split):
  - HDFS $\alpha = 0.01$: Escalated = 0.9%, Coverage = 99.1%, Precision = 85.7%, Selective Risk = 0.0285
  - HDFS $\alpha = 0.05$: Escalated = 4.8%, Coverage = 95.2%, Precision = 18.0%, Selective Risk = 0.0284
  - BGL $\alpha = 0.20$: Escalated = 19.0%, Coverage = 81.0%, Precision = 68.4%, Recall = 36.1%
- Determinism Check: Running Phase 4 pipeline multiple times yields identical model losses, scores, thresholds, and confusion matrices.
- Rule 1 Test Guard: Programmatically verified via `guard_no_test_split` regression tests.

## Next Authorized Phase
Phase 5 — Retrieval-augmented incident explanation and faithfulness checking (PENDING HUMAN APPROVAL)
