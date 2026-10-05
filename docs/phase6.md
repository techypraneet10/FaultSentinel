# SentinelLog Phase 6: Retrieval Reranking & Evidence Selection

## 1. Overview & Research Objective

Phase 6 introduces the **evidence reranking and selection layer** into SentinelLog's selective triage cascade. In Phase 5, escalated log windows retrieved a raw candidate set of $k=5$ historical TRAIN log chunks via cosine similarity over TF-IDF template embeddings. However, raw nearest-neighbor retrieval frequently yields high redundancy (near-duplicate event sequences and repeated source windows).

Phase 6 implements a deterministic, label-free, CPU-friendly **Maximum Marginal Relevance (MMR)** evidence selection mechanism to compress the candidate set into a smaller, higher-quality, and better-diversified evidence set ($k=3$) suitable for downstream root-cause analysis and provenance.

```
RAW LOG WINDOW
      ↓
Phase 4 Split-Conformal Selective Gate
      ↓
┌───────────────────────┬────────────────────────────────────────┐
│ AUTO-CLEAR (95-98%)   │ ESCALATE (2-5%)                        │
│ Bypasses Retrieval &  │ 1. Phase 5 Candidate Retrieval (k=5)   │
│ Reranking Entirely    │ 2. Phase 6 MMR Reranking & Selection   │
│ (Zero LLM/Search Cost)│ 3. Compact Evidence Set (k=3)          │
│                       │ 4. STOP (No LLM generation in Phase 6) │
└───────────────────────┴────────────────────────────────────────┘
```

**Central Research Question**:
> *Can reranking and diversity-aware evidence selection improve the usefulness of retrieved evidence while reducing redundancy, without using anomaly labels, future information, calibration labels, or test data?*

**Absolute Scope Boundary**:
Phase 6 is strictly concerned with **evidence quality, ranking, and diversity-aware selection**.
**NO LLM generation, OpenAI/Anthropic APIs, RAG answer generation, explanation synthesis, faithfulness checking, citation generation, provenance engine, FastAPI, or Docker serving are implemented in Phase 6.**

---

## 2. Phase 5 → Phase 6 Interface

Phase 6 strictly consumes the frozen candidate set produced by Phase 5:

$$\text{candidates} = \text{Phase5.retrieve}(\text{query}, k=5)$$
$$\text{selected} = \text{Phase6.rerank\_and\_select}(\text{query}, \text{candidates}, \text{retrieval\_k}=5)$$

### 2.1 Preserved Phase 5 Signal
Phase 6 preserves all Phase 5 retrieval attributes without overwriting them:
- `retrieval_score`: Original Phase 5 cosine similarity $s(q, d) \in [-1.0, 1.0]$.
- `retrieval_rank`: Original 1-indexed retrieval position.
- `chunk_id`: Deterministic SHA-256 content-derived identifier.
- `source_window_id`: Window identifier of historical incident chunk.

### 2.2 Phase 6 Output Schema
The selected evidence is encapsulated in typed dataclasses ([`SelectedEvidence`](file:///d:/FaultSentinel/sentinellog/retrieval/reranking_schemas.py#L13-L37) and [`EvidenceSelectionResult`](file:///d:/FaultSentinel/sentinellog/retrieval/reranking_schemas.py#L40-L75)):
- `selected_rank`: 1-indexed selection order.
- `selection_score`: MMR score at the step of selection.
- `redundancy_penalty`: Maximum cosine similarity to any previously selected evidence item ($0.0$ for the first selected item).

---

## 3. Mathematical Formulation & Selection Algorithm

### 3.1 Relevance Signal
The base relevance signal is the Phase 5 cosine similarity:
$$\text{relevance}(d) = \text{candidate.similarity}$$

### 3.2 Redundancy Signal
Redundancy between a candidate $d$ and the set of already selected items $S$ is evaluated deterministically in the vector embedding space of the fitted Phase 5 local embedding model:
$$\text{redundancy}(d, S) = \max_{s \in S} \cos(v_d, v_s)$$
where $v_d, v_s$ are $L_2$-normalized TF-IDF template vector representations.

### 3.3 MMR Selection Formula
For an unselected candidate $d \in C \setminus S$:
$$\text{score}(d) = \begin{cases}
\text{relevance}(d) & \text{if } S = \emptyset \\
\lambda \cdot \text{relevance}(d) - (1 - \lambda) \cdot \max_{s \in S} \cos(v_d, v_s) & \text{if } S \neq \emptyset
\end{cases}$$

### 3.4 Parameters
- $\lambda = 0.70$: Balances relevance ($70\%$) and diversity ($30\%$). Configurable in $[0.0, 1.0]$.
- `retrieval_k = 5`: Number of candidates retrieved in Phase 5.
- `evidence_k = 3`: Budget of selected evidence chunks. Enforces $\text{evidence\_k} \le \text{retrieval\_k}$.

### 3.5 Strictly Deterministic Tie-Breaking
Candidates are sorted lexicographically by a 3-tuple:
1. `selection_score` DESC
2. `retrieval_score` DESC
3. `chunk_id` ASC (content-derived SHA-256 string)

This guarantees deterministic ordering across executions without relying on non-deterministic data structures or random seeds.

---

## 4. Research Integrity & Leakage Controls

1. **Rule 1 (Test Set Protection)**:
   - `data/test/` remains strictly locked and untouched (`test_used: false`).
   - The test set is neither read, embedded, scored, nor referenced.
2. **Train-Only Corpus**:
   - The candidate pool is derived exclusively from historical `train.jsonl` data.
3. **No Calibration Tuning of Primary Reranker**:
   - The primary reranking parameters ($\lambda = 0.70, \text{evidence\_k} = 3$) are documented engineering defaults and were **not** chosen by optimizing anomaly detection metrics over calibration labels.
4. **Label-Free Primary Pipeline**:
   - Anomaly labels are strictly forbidden from query objects and searchable texts via [`guard_query_does_not_contain_labels`](file:///d:/FaultSentinel/sentinellog/retrieval/guards.py).
   - The reranker's selection logic is mathematically invariant to whether candidates are normal or anomalous.

---

## 5. Experimental Results & Diagnostics

Phase 6 was evaluated across the escalated windows of the CALIBRATION partition for both HDFS and BGL.

### 5.1 Primary Pipeline Diagnostics

| Metric | HDFS | BGL |
|---|---|---|
| Total Evaluated Windows | 814 | 100 |
| AUTO-CLEAR Windows | 775 (95.21%) | 98 (98.00%) |
| ESCALATE Windows | 39 (4.79%) | 2 (2.00%) |
| Retrieval Candidates ($k$) | 5 | 5 |
| Selected Evidence Budget ($k$) | 3 | 3 |
| Evidence Compression Ratio | 60.0% | 60.0% |
| Mean Relevance (Candidates) | 0.9086 | 0.0265 |
| Mean Relevance (Selected) | 0.9239 | 0.0240 |
| Relevance Delta | +0.0152 | -0.0025 |
| Mean Pairwise Sim (Candidates) | 0.9478 | 0.5908 |
| Mean Pairwise Sim (Selected) | 0.9184 | 0.3227 |
| **Pairwise Redundancy Reduction** | **-0.0294** | **-0.2681** |
| Unique Chunks Retrieved (Cand $\to$ Sel) | 15 $\to$ 9 | 5 $\to$ 3 |
| Unique Windows Retrieved (Cand $\to$ Sel) | 15 $\to$ 9 | 5 $\to$ 3 |

### 5.2 Controlled Research Ablations

#### Ablation A: Phase 5 Top-3 Retrieval vs Phase 5 + MMR (5 $\to$ 3)
- **HDFS**:
  - Phase 5 Top-3 Retrieval: Relevance = 0.9244, Pairwise Similarity = 0.9244
  - MMR (5 $\to$ 3): Relevance = 0.9239, Pairwise Similarity = 0.9184
  - Redundancy Reduction: **0.0060**
- **BGL**:
  - Phase 5 Top-3 Retrieval: Relevance = 0.0346, Pairwise Similarity = 0.9804
  - MMR (5 $\to$ 3): Relevance = 0.0240, Pairwise Similarity = 0.3227
  - Redundancy Reduction: **0.6577** (Substantial diversity improvement over near-duplicate Top-3 candidates)

#### Ablation B: Lambda Sensitivity
| Lambda ($\lambda$) | HDFS Relevance | HDFS Pairwise Sim | BGL Relevance | BGL Pairwise Sim |
|---|---|---|---|---|
| 1.00 (Pure Relevance) | 0.9244 | 0.9244 | 0.0346 | 0.9804 |
| 0.85 | 0.9239 | 0.9184 | 0.0250 | 0.3249 |
| **0.70 (Default)** | **0.9239** | **0.9184** | **0.0240** | **0.3227** |
| 0.50 | 0.9239 | 0.9184 | 0.0240 | 0.3227 |
| 0.00 (Pure Diversity) | 0.9239 | 0.9184 | 0.0240 | 0.3227 |

*Finding*: On BGL, introducing even a mild diversity penalty ($\lambda = 0.85$ or $0.70$) drastically breaks candidate vector-space redundancy (pairwise similarity collapses from $0.9804$ to $0.3227$). At $\lambda=1.00$, the 3 selected chunks are `['8bdd5020', '5e100dd8', 'a88b671e']` with pairwise similarity $0.9804$. At $\lambda=0.85$, chunk `'003080c3'` (orthogonal with penalty $0.0$) replaces the redundant `'a88b671e'`. At $\lambda \le 0.70$, the higher diversity penalty drives MMR to select `'a88b671e'` over `'5e100dd8'`, achieving the minimum pairwise similarity of $0.3227$. On HDFS, high structural repetition across block lifecycle templates keeps pairwise similarity high, but MMR still systematically penalizes identical candidate chunks.

#### Ablation C: Evidence Budget Compression
| Budget ($k$) | HDFS Compression | HDFS Relevance | HDFS Pairwise Sim | BGL Compression | BGL Relevance | BGL Pairwise Sim |
|---|---|---|---|---|---|---|
| $k=1$ | 20.0% | 1.0000 | 0.0000 | 20.0% | 0.0433 | 0.0000 |
| **$k=3$** | **60.0%** | **0.9239** | **0.9184** | **60.0%** | **0.0240** | **0.3227** |
| $k=5$ | 100.0% | 0.9086 | 0.9478 | 100.0% | 0.0265 | 0.5908 |

---

## 6. Determinism & Verification

- Repeated execution of the Phase 6 pipeline produces bitwise-identical `evidence_selection.jsonl` files:
  - HDFS `evidence_selection.jsonl`: `c634b7688b2a507c9bee3a2533f91e6b00aa5c7a76e0f9086d08fc85eceef9e6`
  - BGL `evidence_selection.jsonl`: `200e9a3f34e59e9dfdb1d8e910666bae8ae20b82a8e827a2c9d55de451fbcdc2`
- Diagnostic metrics content hash (excluding runtime timing) is completely invariant across runs:
  - HDFS `reranking_diagnostics.json` content hash: `e66500a28b24419d29420dc6d86044fe1d31b298b7f39c69bb23f8429b3a0a07`
  - BGL `reranking_diagnostics.json` content hash: `50f30c5470009382140384f41475ab10e4958ed34f9370bb287a392acdb66bdb`
- Full test suite: **111 tests passing** across the entire SentinelLog codebase.
- Code compilation (`compileall`): Clean across `sentinellog`, `tests`, and `scripts`.
- Rule 1 test set protection verified: `test_used: false` recorded across all manifests.
- Unsupervised calibration protection verified: `calibration_used_for_fitting: false` recorded across all manifests.

---

## 7. Research Limitations

1. **Heuristic Vector Diversity**: MMR is a greedy heuristic that balances vector cosine distance; structural diversity in vector space does not guarantee contextual sufficiency for an arbitrary incident.
2. **Template Representation**: TF-IDF embeddings capture template token occurrences but lack deep semantic understanding of parameter variables.
3. **Repetition in Log Datasets**: Standard system log datasets (especially HDFS block sessions) exhibit massive structural repetition; redundancy reduction is bounded by corpus variety.
4. **No LLM Quality Guarantee**: Decreasing vector redundancy has not yet been evaluated on actual LLM generation or hallucination rates (deferred to later phases).
5. **Not an Anomaly Detector**: Phase 6 evidence reranking does not alter the anomaly detection metrics or false-alarm rates established by Phase 4.
