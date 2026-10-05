# SentinelLog Build Progress

## Project
SentinelLog — Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs

## Current Phase
Phase 6 — Retrieval Reranking & Evidence Selection

## Status
COMPLETE (Phase 6 MMR evidence reranking and selection implemented, verified, tested, and committed; awaiting human verification)

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

## Completed (Phase 6)
- [x] Frozen Phase 5 candidate consumption: Phase 6 takes Phase 5 retrieval output ($k=5$) as candidates without mutating Phase 5 logic.
- [x] Retrieval score preservation: Original Phase 5 retrieval scores, ranks, and chunk IDs preserved intact on all selected items.
- [x] MMR-style evidence reranking: Maximum Marginal Relevance ($\lambda \cdot \text{rel} - (1-\lambda) \cdot \text{max\_sim}$) implemented with configurable $\lambda$ (default 0.70).
- [x] Compact evidence budget selection: Configurable `evidence_k` (default 3) strictly enforcing $\text{evidence\_k} \le \text{retrieval\_k}$.
- [x] Strictly deterministic tie-breaking: `selection_score` DESC $\to$ `retrieval_score` DESC $\to$ `chunk_id` ASC.
- [x] Label leakage protection: Primary reranker and selection logic are strictly label-free; fail-closed guards prevent label exposure.
- [x] Cascade integration (`GatedEvidencePipeline`): `AUTO-CLEAR` bypasses retrieval and selection; `ESCALATE` invokes retrieval and MMR selection.
- [x] Controlled research ablations:
  - Ablation A: Phase 5 Top-3 Retrieval vs Phase 5 + MMR Selection ($5 \to 3$).
  - Ablation B: Lambda Sensitivity ($\lambda \in \{1.0, 0.85, 0.70, 0.50, 0.0\}$).
  - Ablation C: Evidence Budget Compression ($k \in \{1, 3, 5\}$).
- [x] Phase 6 standalone CLI runner and diagnostics generator (`sentinellog/retrieval/phase6_runner.py`, `configs/phase6.yaml`).
- [x] Generated reproducible artifacts in `results/phase6/` (`phase6_report.md`, `phase6_report.json`, manifests, `evidence_selection.jsonl`, `reranking_diagnostics.json`).
- [x] Phase 6 unit and integration test suite with 15 comprehensive tests (`tests/test_evidence_selection.py`).
- [x] Full test suite passing (111/111 tests passing in 24s) on Python 3.12.4 CPU `.venv`.
- [x] Determinism verified: Repeated execution yields identical bitwise SHA-256 hashes.
- [x] Comprehensive Phase 6 documentation (`docs/phase6.md`).

## Not Completed
- Phase 7 — Frozen evaluation over benchmark test sets, provenance and citation verification
- Phase 8 — Production service and API endpoint serving
- Phase 9 — Final deployment, containerization, and reproducibility artifacts

## Test Set
LOCKED (Rule 1)

## Test-set Access
FORBIDDEN until Phase 7.
(All Phase 6 models, tokenizers, corpus construction, and selective retrieval/reranking evaluations were conducted exclusively on TRAIN and CALIBRATION. `test_used: false` verified across all manifests.)

## Last Validation
- Date: 2026-10-05
- Pytest: 111 passed in 23.56s (0 failed, 0 warnings across all 7 test modules)
- Syntax/Bytecode check: `.venv\Scripts\python.exe -m compileall -q sentinellog tests scripts` (Clean, exit code 0)
- Gated Selective Evidence Selection Diagnostics (CALIBRATION split at $\alpha=0.05$, $k=5 \to 3$, $\lambda=0.70$):
  - HDFS: 814 windows evaluated $\to$ 775 (95.2%) Auto-Cleared, 39 (4.8%) Escalated, 117 evidence chunks selected (relevance = 0.9239, pairwise similarity reduced by 0.0294)
  - BGL: 100 windows evaluated $\to$ 98 (98.0%) Auto-Cleared, 2 (2.0%) Escalated, 6 evidence chunks selected (relevance = 0.0240, pairwise similarity reduced by 0.2681)
- Determinism Check: Running Phase 6 pipeline yields bit-for-bit identical SHA-256 artifact hashes:
  - HDFS `evidence_selection.jsonl`: `c634b7688b2a507c9bee3a2533f91e6b00aa5c7a76e0f9086d08fc85eceef9e6`
- Rule 1 Test Guard: Programmatically verified via `guard_no_test_split` regression tests.

## Next Authorized Phase
Phase 7 — Frozen evaluation over benchmark test sets, provenance and citation verification (PENDING HUMAN APPROVAL)
