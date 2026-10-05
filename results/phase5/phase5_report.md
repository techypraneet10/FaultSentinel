# Phase 5: Leakage-Safe Contextual Retrieval Infrastructure Report

> **RESEARCH INTEGRITY GUARDRAIL**: Retrieval corpus and embedding models are constructed **EXCLUSIVELY** from **TRAIN**. The **TEST** partition remains strictly **FROZEN** under Rule 1. Non-escalated windows (`AUTO-CLEAR`) strictly bypass retrieval.

## Dataset: HDFS

- **Corpus Size ($N_{train}$)**: 2,450 chunks
- **Corpus Split**: `train` (CALIBRATION / TEST access strictly forbidden)
- **Embedding Model**: `template_tfidf_v1` (Dimension: 16, Vocab Hash: `f9d41496e5c81b6e...`)
- **Mean Vector Norm**: 1.0000 (Zero-Norm Vectors: 0)
- **Retrieval Configuration**: $k = 5$, Metric: `cosine`, Filter: `train_only_same_dataset_exclude_self`

### Gated Selective Retrieval Evaluation (CALIBRATION Split)

- **Total Windows Evaluated**: 814
- **Auto-Cleared Windows**: 775 (95.2%) $\to$ **Retrieval Bypassed (0 LLM/Retrieval Cost)**
- **Escalated Windows**: 39 (4.8%) $\to$ **Contextual Retrieval Invoked**
- **Evidence Chunks Retrieved**: 195 (Unique: 15)
- **Self-Retrieval Rate**: 0.0% (Self-exclusion verified)
- **Duplicate Retrieval Rate**: 92.3%

### Similarity Distribution (Retrieved Evidence)

| Min Similarity | P25 | Median | P75 | Max Similarity | Mean |
|---|---|---|---|---|---|
| 0.2521 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9086 |

### Diagnostic Label Analysis (Research Inspection Only)

> *Post-hoc research diagnostic only. Labels were NOT used in query or embedding text.*

- Anomalous Evidence Chunks: 24 / 195 (12.3%)

---

## Dataset: BGL

- **Corpus Size ($N_{train}$)**: 300 chunks
- **Corpus Split**: `train` (CALIBRATION / TEST access strictly forbidden)
- **Embedding Model**: `template_tfidf_v1` (Dimension: 19, Vocab Hash: `3917134514406649...`)
- **Mean Vector Norm**: 1.0000 (Zero-Norm Vectors: 0)
- **Retrieval Configuration**: $k = 5$, Metric: `cosine`, Filter: `train_only_same_dataset_exclude_self`

### Gated Selective Retrieval Evaluation (CALIBRATION Split)

- **Total Windows Evaluated**: 100
- **Auto-Cleared Windows**: 98 (98.0%) $\to$ **Retrieval Bypassed (0 LLM/Retrieval Cost)**
- **Escalated Windows**: 2 (2.0%) $\to$ **Contextual Retrieval Invoked**
- **Evidence Chunks Retrieved**: 10 (Unique: 5)
- **Self-Retrieval Rate**: 0.0% (Self-exclusion verified)
- **Duplicate Retrieval Rate**: 50.0%

### Similarity Distribution (Retrieved Evidence)

| Min Similarity | P25 | Median | P75 | Max Similarity | Mean |
|---|---|---|---|---|---|
| 0.0000 | 0.0288 | 0.0288 | 0.0316 | 0.0433 | 0.0265 |

### Diagnostic Label Analysis (Research Inspection Only)

> *Post-hoc research diagnostic only. Labels were NOT used in query or embedding text.*

- Anomalous Evidence Chunks: 10 / 10 (100.0%)

---

