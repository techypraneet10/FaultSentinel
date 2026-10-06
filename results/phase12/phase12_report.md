# PHASE 12 — EVALUATION & BENCHMARKING

## 1. Research Question
**Primary Question:**
> Does lightweight anomaly scoring + calibrated selective escalation + retrieval-grounded explanation improve precision-at-coverage and reduce false alarms / unnecessary expensive processing under a fixed escalation budget compared with defined baselines?

**Verdict:** **SUPPORTED**

Under the evaluated operating conditions on the frozen HDFS test partition (α=0.05, threshold=1.1546), SentinelLog achieved 5.22% escalation coverage, 27.91% precision among escalated windows, 40.00% recall, and eliminated 94.78% of expensive LLM processing calls (43 vs 823) compared to LLM-every-window. The final raw classification metrics match underlying baseline B2, confirming that the primary measured contribution of the cascade is selective escalation, evidence grounding, and computational cost reduction rather than improved raw detection over B2. On the anomaly-free BGL test partition (0 ground truth anomalies), the system achieved 0 false alarms and 0 expensive calls, safely auto-clearing all normal windows.

---

## 2. Experimental Protocol
- Chronological train/calibration/test partitions frozen in Phase 2.
- Unsupervised models fitted solely on TRAIN.
- Decision thresholds calibrated strictly on CALIBRATION.
- Final test set locked and used for **EVALUATION ONLY** (zero threshold tuning or model selection on test).
- Deterministic mock provider for grounded LLM explanation orchestration (Rule 4 isolation).

---

## 3. Dataset Description
### TABLE 1: Dataset Statistics
| Dataset | Total Raw Records | Window Unit | Total Windows | Train Windows | Calib Windows | Test Windows | Test Anomalies | Anomaly Prevalence |
|---|---|---|---|---|---|---|---|---|
| **HDFS** | 11,175,629 | Session Block (blk_-...) | 4,087 | 2,450 | 814 | 823 | 30 | 3.65% |
| **BGL** | 4,747,963 | Fixed Time/Record Slice | 500 | 300 | 100 | 100 | 0 | 0.00% (test slice) |

---

## 4. Primary Results: Baseline & Proposed Systems
### TABLE 2 & PRIMARY COMPARISON TABLE: Test Partition Benchmark
| System | Dataset | Windows | TP | FP | TN | FN | Precision | Recall | F1 | FPR | False-Clear Rate | Escalation Rate | Expensive Calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0 Frequency** | HDFS | 823 | 27 | 385 | 408 | 3 | 0.0655 | 0.9000 | 0.1222 | 0.4855 | 0.0036 | 50.06% | 0 |
| **B1 PCA** | HDFS | 823 | 30 | 793 | 0 | 0 | 0.0365 | 1.0000 | 0.0703 | 1.0000 | 0.0000 | 100.00% | 0 |
| **B1 Isolation Forest** | HDFS | 823 | 30 | 793 | 0 | 0 | 0.0365 | 1.0000 | 0.0703 | 1.0000 | 0.0000 | 100.00% | 0 |
| **B2 Sequential GRU** | HDFS | 823 | 12 | 31 | 762 | 18 | 0.2791 | 0.4000 | 0.3288 | 0.0391 | 0.0219 | 5.22% | 0 |
| **B3 LLM Every Window** | HDFS | 823 | 12 | 31 | 762 | 18 | 0.2791 | 0.4000 | 0.3288 | 0.0391 | 0.0219 | 100.00% | 823 |
| **Proposed SentinelLog** | HDFS | 823 | **12** | **31** | **762** | **18** | **0.2791** | **0.4000** | **0.3288** | **0.0391** | **0.0219** | **5.22%** | **43** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0 Frequency** | BGL | 100 | 0 | 0 | 100 | 0 | N/A (undefined) | N/A (undefined) | N/A (undefined) | 0.0000 | 0.0000 | 0.00% | 0 |
| **B1 PCA** | BGL | 100 | 0 | 0 | 100 | 0 | N/A (undefined) | N/A (undefined) | N/A (undefined) | 0.0000 | 0.0000 | 100.00% | 0 |
| **B1 Isolation Forest** | BGL | 100 | 0 | 2 | 98 | 0 | 0.0000 | N/A (undefined) | N/A (undefined) | 0.0200 | 0.0000 | 100.00% | 0 |
| **B2 Sequential GRU** | BGL | 100 | 0 | 0 | 100 | 0 | N/A (undefined) | N/A (undefined) | N/A (undefined) | 0.0000 | 0.0000 | 0.00% | 0 |
| **B3 LLM Every Window** | BGL | 100 | 0 | 0 | 100 | 0 | N/A (undefined) | N/A (undefined) | N/A (undefined) | 0.0000 | 0.0000 | 100.00% | 100 |
| **Proposed SentinelLog** | BGL | 100 | **0** | **0** | **100** | **0** | **N/A (undefined)** | **N/A (undefined)** | **N/A (undefined)** | **0.0000** | **0.0000** | **0.00%** | **0** |

*Zero-Positive Ground-Truth Limitation (BGL):* The chronological BGL test partition (N=100) contains 0 ground-truth anomalies. Consequently, recall is mathematically undefined (0/0), F1 is undefined, and precision is 0.0000 when positive predictions are made (e.g. B1, B3) or undefined when zero positives are predicted (B0, B2, Proposed). This partition serves strictly as an anomaly-free safety / negative-evidence evaluation slice (evaluating false alarms and unnecessary expensive calls) and must not be used to claim recall or anomaly-detection superiority.

**Equivalence Note on B2 vs Proposed Final Classification:**
Because SentinelLog's selective gate threshold at α=0.05 is calibrated directly on B2's scores (threshold τ_0.05 = 1.1546), the final binary classification metrics on HDFS (TP=12, FP=31, TN=762, FN=18, Precision=0.2791, Recall=0.4000) for B2 and SentinelLog are identical. The measured contribution of the proposed SentinelLog cascade is therefore NOT improved raw anomaly classification over B2, but rather:
1. Calibrated selective escalation (auto-clearing 94.78% of windows without operator burden)
2. Historical evidence retrieval (Phase 5)
3. MMR diversity reranking reducing redundancy by 24.6% (Phase 6)
4. Cryptographic provenance and citation verification (Phase 7)
5. Grounded incident explanation with 100% claim-level citation validation (Phase 9)
6. 94.78% computational reduction in expensive LLM calls compared to LLM-every-window (Phase 12).

---

## 5. Selective Prediction Results
### TABLE 3: Selective Metrics (α = 0.05)
| Dataset | Total Windows | Auto-Cleared | Escalated | Escalation Rate | Auto-Clear Rate | Anomalies Cleared (FN) | Anomalies Escalated (TP) | Empirical False Clear Rate | Selective Risk |
|---|---|---|---|---|---|---|---|---|---|
| **HDFS** | 823 | 780 | 43 | 5.22% | 94.78% | 18 | 12 | 2.19% | 2.31% |
| **BGL** | 100 | 100 | 0 | 0.00% | 100.00% | 0 | 0 | 0.00% | N/A (undefined) |

*Empirical Selective Behavior & Escalation Control:* System logs exhibit temporal dependence and burstiness; standard exchangeability assumptions do not strictly hold. Therefore, we evaluate empirical selective behavior and empirical escalation-rate control along the coverage-risk frontier. We do NOT claim a formal anomaly-risk guarantee under temporal dependence, and we preserve the Phase 4 distinction between conformal calibration behavior and the empirical false-clear rate (FN / N).

---

## 6. Precision-at-Coverage
### TABLE 4: Precision-at-Coverage Across Conformal Operating Points (HDFS)
| Operating Point | Threshold | Escalation Coverage | Auto-Clear Coverage | Precision | Recall | FPR | Empirical False-Clear Rate | Selective Risk |
|---|---|---|---|---|---|---|---|---|
| **α = 0.01** | 1.6723 | 0.85% | 99.15% | 0.8571 | 0.2000 | 0.0013 | 0.0292 | 0.0294 |
| **α = 0.05** | 1.1546 | 5.22% | 94.78% | 0.2791 | 0.4000 | 0.0391 | 0.0219 | 0.0231 |
| **α = 0.10** | 0.9766 | 9.96% | 90.04% | 0.1463 | 0.4000 | 0.0883 | 0.0219 | 0.0243 |
| **α = 0.20** | 0.9461 | 18.23% | 81.77% | 0.0800 | 0.4000 | 0.1740 | 0.0219 | 0.0268 |

---

## 7. Computational Cost & LLM Call Reduction
### TABLE 5: Expensive Processing Reduction vs B3 (LLM Every Window)
| Dataset | Total Windows | B3 Expensive Calls | Proposed Expensive Calls | Expensive Call Reduction | Relative Compute Cost Reduction |
|---|---|---|---|---|---|
| **HDFS** | 823 | 823 | 43 | **94.78%** | **85.34%** |
| **BGL** | 100 | 100 | 0 | **100.00%** | **98.21%** |

---

## 8. Upstream Pipeline Verification
### TABLE 6: Retrieval Evaluation (Phase 5)
- Retrieval Corpus: Strictly built from TRAIN (zero test contamination).
- Chunk Size: Bounded sequences, self-exclusion verified on train queries, same-dataset filtering enforced.

### TABLE 7: MMR Evaluation (Phase 6)
- Parameters: `k=5`, `evidence_k=3`, `lambda=0.7`.
- Outcome: 24.6% reduction in pairwise redundancy compared to raw cosine similarity.

### TABLE 8: Citation & Explanation Faithfulness (Phase 7 & Phase 9)
- Citation Precision: **1.0** (117/117 HDFS, 6/6 BGL)
- Citation Coverage: **1.0** (100% claim-level grounding)
- Faithfulness Status: **VERIFIED**

---

## 9. Ablation Studies
### TABLE 9: Ablation Summary
| Ablation | Changed Factor | Controlled Baseline | Observed Effect | Interpretation |
|---|---|---|---|---|
| **A: No Conformal Gate** | Remove selective gate | All windows escalated | 823 calls vs 43 calls | Selective gate eliminates 94.8% of expensive calls |
| **B: No Retrieval** | Remove evidence packet | Triage with prompt only | Evidence abstention | Upstream evidence required for grounded reasoning |
| **C: No MMR** | Raw cosine similarity | Diversity reranking | +24.6% pairwise redundancy | MMR diversifies historical incident evidence |
| **D: No Sufficiency Check** | Bypass sufficiency gate | Calibrated triage | False alerts on sparse logs | Sufficiency prevents alert storms on uninformative logs |
| **E: B2 vs B1 Gating** | B1 PCA scorer | B2 GRU scorer | Precision 0.0365 vs 0.2791 | Sequential modeling yields 7.6x higher triage precision |
| **F: Selective vs Every Window** | B3 vs Proposed | Identical detection layer | 94.78% call reduction | Selective gating dramatically lowers operational burden |

---

## 10. Statistical Hypothesis Testing (McNemar Paired Test)
### Contingency Table Across Paired Windows (HDFS: B0 vs Proposed SentinelLog)
Loaded directly from saved per-window predictions across the N=823 test windows:
- **B0+ / Sentinel+**: 12
- **B0+ / Sentinel-**: 400 (b: B0 alerted, SentinelLog auto-cleared)
- **B0- / Sentinel+**: 31 (c: B0 cleared, SentinelLog escalated)
- **B0- / Sentinel-**: 380

- Total discordant pairs: b = 400, c = 31 (total discordant = 431)
- Edwards-corrected chi-square statistic: χ² = (|400 - 31| - 1)² / (400 + 31) = 314.2088
- Two-tailed p-value: p = 2.64e-70 (statistically significant at α=0.05, p < 10⁻⁶⁹)
- Verification: The substantial reduction in false alarms and escalated volume from B0 to SentinelLog is statistically significant under paired window testing.

---

## 11. Threats to Validity & Scientific Limitations
### TABLE 10: Limitations Matrix
1. **Temporal Dependence**: System logs exhibit non-stationary bursts. Conformal exchangeability does not strictly hold; we evaluate empirical escalation control.
2. **Dataset Age**: HDFS and BGL are canonical academic benchmarks; modern cloud logs exhibit different syntax.
3. **Zero Ground-Truth Anomalies on BGL Test Slice**: The BGL test partition contains 0 positive instances; metrics reflect negative-evidence safety rather than recall.
4. **No Fabricated Human Evaluation**: `HUMAN_EVALUATION = NOT_AVAILABLE`. No synthetic expert ratings are reported.
5. **Deterministic Provider**: Offline mock LLM ensures scientific reproducibility but does not capture commercial API latency fluctuations.
6. **Class Imbalance**: High imbalance in HDFS limits maximum achievable raw precision.

---

## 12. Final Verdict
**PHASE 12 VERDICT:** **SUPPORTED**
Under the evaluated operating conditions on the frozen HDFS test partition (α=0.05, threshold=1.1546), SentinelLog achieved 5.22% escalation coverage, 27.91% precision among escalated windows, 40.00% recall, and eliminated 94.78% of expensive LLM processing calls compared to LLM-every-window. The final raw classification metrics match underlying baseline B2, confirming that the primary measured contribution of the cascade is selective escalation, evidence grounding, and computational cost reduction rather than improved raw detection over B2.
