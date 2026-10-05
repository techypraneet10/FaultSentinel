# Phase 6 Summary Report: Retrieval Reranking & Evidence Selection

- **Execution Timestamp**: 2026-10-05T17:19:29.853193+00:00
- **Git Commit**: `523a32da041de59e78610567edb7374370c66433`
- **Rule 1 Enforced (Test Used)**: `False`

## Dataset: HDFS

- **Total Evaluated Windows**: 814
- **AUTO-CLEAR Windows**: 775 (95.21%)
- **ESCALATE Windows**: 39 (4.79%)
- **Retrieval Candidates (k)**: 5
- **Selected Evidence Budget (k)**: 3
- **MMR Lambda**: 0.7
- **Compression Ratio**: 60.0%
- **Mean Relevance**: Candidates = 0.9086, Selected = 0.9239 (Delta: 0.0152)
- **Mean Pairwise Similarity**: Candidates = 0.9478, Selected = 0.9184 (Reduction: 0.0294)
- **Duplicate Selection Rate**: Candidates = 92.31%, Selected = 92.31%

### Controlled Research Ablations

#### Ablation A: Top-3 Retrieval vs MMR Selection (5 -> 3)
- Phase 5 Top-3 Relevance: 0.9244, Pairwise Sim: 0.9244
- MMR (5 -> 3) Relevance: 0.9239, Pairwise Sim: 0.9184
- Pairwise Redundancy Reduction: 0.006

#### Ablation B: Lambda Sensitivity
| Lambda | Relevance | Pairwise Sim |
|---|---|---|
| 1.0 | 0.9244 | 0.9244 |
| 0.85 | 0.9239 | 0.9184 |
| 0.7 | 0.9239 | 0.9184 |
| 0.5 | 0.9239 | 0.9184 |
| 0.0 | 0.9239 | 0.9184 |

#### Ablation C: Evidence Budget Compression
| Evidence Budget (k) | Compression | Relevance | Pairwise Sim |
|---|---|---|---|
| 1 | 20.0% | 1.0 | 0.0 |
| 3 | 60.0% | 0.9239 | 0.9184 |
| 5 | 100.0% | 0.9086 | 0.9478 |

---

## Dataset: BGL

- **Total Evaluated Windows**: 100
- **AUTO-CLEAR Windows**: 98 (98.00%)
- **ESCALATE Windows**: 2 (2.00%)
- **Retrieval Candidates (k)**: 5
- **Selected Evidence Budget (k)**: 3
- **MMR Lambda**: 0.7
- **Compression Ratio**: 60.0%
- **Mean Relevance**: Candidates = 0.0265, Selected = 0.024 (Delta: -0.0025)
- **Mean Pairwise Similarity**: Candidates = 0.5908, Selected = 0.3227 (Reduction: 0.2681)
- **Duplicate Selection Rate**: Candidates = 50.00%, Selected = 50.00%

### Controlled Research Ablations

#### Ablation A: Top-3 Retrieval vs MMR Selection (5 -> 3)
- Phase 5 Top-3 Relevance: 0.0346, Pairwise Sim: 0.9804
- MMR (5 -> 3) Relevance: 0.024, Pairwise Sim: 0.3227
- Pairwise Redundancy Reduction: 0.6577

#### Ablation B: Lambda Sensitivity
| Lambda | Relevance | Pairwise Sim |
|---|---|---|
| 1.0 | 0.0346 | 0.9804 |
| 0.85 | 0.025 | 0.3249 |
| 0.7 | 0.024 | 0.3227 |
| 0.5 | 0.024 | 0.3227 |
| 0.0 | 0.024 | 0.3227 |

#### Ablation C: Evidence Budget Compression
| Evidence Budget (k) | Compression | Relevance | Pairwise Sim |
|---|---|---|---|
| 1 | 20.0% | 0.0433 | 0.0 |
| 3 | 60.0% | 0.024 | 0.3227 |
| 5 | 100.0% | 0.0265 | 0.5908 |

---

