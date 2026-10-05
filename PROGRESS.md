# SentinelLog Build Progress

## Project
SentinelLog — Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs

## Current Phase
Phase 5 — Leakage-Safe Contextual Retrieval Infrastructure

## Status
COMPLETE (Phase 5 retrieval infrastructure verified, tested, and committed; awaiting human authorization to proceed to Phase 6)

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
- [x] Target alpha sweep ($\alpha \in \{0.01, 0.05, 0.10, 0.20\}$) evaluating coverage, selective risk, and empirical false clear rate
- [x] Comprehensive ablations: Heuristic threshold vs Conformal (Ablation A), B1 PCA vs B2 GRU (Ablation B), Calibration sample size sensitivity (Ablation C)
- [x] Standalone Phase 4 CLI runner and report generator (`sentinellog/scoring/phase4_runner.py`, `configs/phase4.yaml`)
- [x] Phase 4 unit and integration test suite with 16 comprehensive tests (`tests/test_phase4.py`)
- [x] Post-audit statistical interpretation correction:
  - Formally distinguished Conformal Score-Tail / Escalation Control ($P(S_{test} > \hat{\tau}_\alpha) \le \alpha$) from Anomaly False-Negative Risk Control ($P(\text{ANOMALY AND AUTO-CLEAR}) \le \alpha$).
  - Clarified that unsupervised calibration does not use anomaly labels; anomaly false-clear rate is an empirical diagnostic, not a conformal guarantee.
  - Renamed metric to `empirical_false_clear_rate` (preserving `empirical_miscoverage` alias).
  - Clarified BGL research finding: 2% escalation strictly respects 5% budget; 35% false-clear rate reflects 36% anomaly prevalence exceeding 5% budget.
  - Proved mathematical equivalence between strict threshold rule ($s > \hat{\tau}_\alpha$) and p-value rule ($p(s) \le \alpha$) when $n \ge \lceil 1/\alpha \rceil - 1$, and documented boundary behavior when $n < 1/\alpha - 1$.
  - Added 19 dedicated verification tests (`tests/test_conformal_verification.py`) covering ties, threshold equality, infinitesimals, repeated extrema, and small $n$.
- [x] Complete test suite passing (77/77 tests passing in 31s) on Python 3.12.4 CPU `.venv`
- [x] Comprehensive Phase 4 documentation updated (`docs/phase4.md`, `results/phase4/phase4_report.md`)

## Completed (Phase 5)
- [x] Fail-closed split validation and Rule 1 test-set protection guards (`sentinellog/retrieval/guards.py`)
- [x] Label leakage protection: automated verification that ground-truth labels never appear in chunk text or queries (`sentinellog/retrieval/guards.py`)
- [x] Retrieval data schemas: `RetrievalChunk`, `RetrievalQuery`, `RetrievedEvidence`, `GatedRetrievalResult` (`sentinellog/retrieval/schemas.py`)
- [x] Contextual chunking and deterministic SHA-256 chunk ID derivation (`sentinellog/retrieval/chunking.py`)
- [x] Deterministic local template TF-IDF embedding model fitted strictly on TRAIN texts (`sentinellog/retrieval/embeddings.py`)
- [x] Safe cosine similarity engine with L2 normalization, safe zero-norm handling, and deterministic tie-breaking (`sentinellog/retrieval/engine.py`)
- [x] Self-retrieval exclusion and dataset isolation (HDFS vs BGL) (`sentinellog/retrieval/engine.py`)
- [x] Gated selective retrieval pipeline: normal windows receive `AUTO-CLEAR` (0 search cost); only `ESCALATE` windows invoke retrieval (`sentinellog/retrieval/gated.py`)
- [x] Standalone Phase 5 CLI runner and diagnostics generator (`sentinellog/retrieval/phase5_runner.py`, `configs/phase5.yaml`)
- [x] Generated reproducible artifacts in `results/phase5/` (HDFS: 2,450 chunks, BGL: 300 chunks; bit-for-bit identical hashes across runs)
- [x] Phase 5 unit and integration test suite with 19 comprehensive tests (`tests/test_retrieval.py`)
- [x] Complete test suite passing (96/96 tests passing in 34s) on Python 3.12.4 CPU `.venv`
- [x] Comprehensive Phase 5 documentation (`docs/phase5.md`, `results/phase5/phase5_report.md`)

## Not Completed
- Phase 6 — Full cascade integration and selective prediction triage
- Phase 7 — Frozen evaluation over benchmark test sets
- Phase 8 — Production service and API endpoint serving
- Phase 9 — Final deployment, containerization, and reproducibility artifacts

## Test Set
LOCKED (Rule 1)

## Test-set Access
FORBIDDEN until Phase 7.
(All Phase 5 models, tokenizers, corpus construction, and selective retrieval evaluations were conducted exclusively on TRAIN and CALIBRATION. `test_used: false` verified across all manifests.)

## Last Validation
- Date: 2026-10-05
- Pytest: 96 passed in 33.60s (0 failed, 0 warnings across all 6 test modules)
- Syntax/Bytecode check: `.venv\Scripts\python.exe -m compileall -q sentinellog tests scripts` (Clean, exit code 0)
- Retrieval Corpus Sizes (TRAIN only): HDFS = 2,450 chunks; BGL = 300 chunks
- Embedding Dimensions: HDFS = 16 dimensions; BGL = 19 dimensions
- Gated Selective Retrieval Diagnostics (CALIBRATION split at $\alpha=0.05$):
  - HDFS: 814 windows evaluated $\to$ 775 (95.2%) Auto-Cleared (Bypassed), 39 (4.8%) Escalated, 195 evidence chunks retrieved (0.0% self-retrieval)
  - BGL: 100 windows evaluated $\to$ 98 (98.0%) Auto-Cleared (Bypassed), 2 (2.0%) Escalated, 10 evidence chunks retrieved (0.0% self-retrieval)
- Determinism Check: Running Phase 5 pipeline multiple times yields identical SHA-256 artifact hashes:
  - HDFS corpus: `b5b70fdec940e888d6b3d52ca780638dc9c7a25881657371e18c6313e4b8df49`
  - HDFS embeddings: `0bb38c7037ce42cf7729ff2726137eaee1da582e5a4581287b799c105ae27b1d`
  - BGL corpus: `d80e94505949fce1661a1dfff8ad5331fbe63870dc3f753d2b0fe041df44baab`
  - BGL embeddings: `6ff0f8c81bf93944f3817a60e3d7b4fcbf4455cd2cbff6fd95ac071fb4428784`
- Rule 1 Test Guard: Programmatically verified via `guard_no_test_split` regression tests.

## Next Authorized Phase
Phase 6 — Full cascade integration and selective prediction triage (PENDING HUMAN APPROVAL)
