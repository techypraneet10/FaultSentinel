# SentinelLog Phase 5: Leakage-Safe Contextual Retrieval Infrastructure

## 1. Overview & Research Objective

Phase 5 establishes the **contextual retrieval layer** for SentinelLog. In the triage cascade, when an anomaly scorer and calibrated split-conformal gate escalate an uncertain or high-risk log window, historical incident context must be provided to ground downstream root-cause analysis:

```
RAW LOGS
    ↓
Drain3 Parser
    ↓
Log Windows
    ↓
B1/B2 Anomaly Scoring
    ↓
Split-Conformal Selective Gate
    ↓
┌───────────────────────┬────────────────────────┐
│ AUTO-CLEAR (95-98%)   │ ESCALATE (2-5%)        │
│ Bypasses Retrieval    │ Contextual Retrieval   │
│ (Zero LLM/Search Cost)│ Top-k Historical TRAIN │
└───────────────────────┴────────────────────────┘
```

**Central Research Question**:
> *Does lightweight anomaly scoring + calibrated selective escalation + retrieval-grounded context improve incident triage precision-at-coverage while drastically reducing false alarms and unnecessary LLM costs?*

Phase 5 implements **strictly the retrieval infrastructure**.
**NO LLM generation, explanation generation, faithfulness checking, external API calls, or serving layers are implemented in Phase 5.**

---

## 2. Architecture & Pipeline Components

The Phase 5 retrieval infrastructure consists of:
1. [`sentinellog.retrieval.guards`](file:///d:/FaultSentinel/sentinellog/retrieval/guards.py): Split validation, Rule 1 test-set protection, and label leakage prevention.
2. [`sentinellog.retrieval.schemas`](file:///d:/FaultSentinel/sentinellog/retrieval/schemas.py): Explicit dataclasses for `RetrievalChunk`, `RetrievalQuery`, `RetrievedEvidence`, and `GatedRetrievalResult`.
3. [`sentinellog.retrieval.chunking`](file:///d:/FaultSentinel/sentinellog/retrieval/chunking.py): Deterministic token formatting and SHA-256 chunk identifier derivation.
4. [`sentinellog.retrieval.embeddings`](file:///d:/FaultSentinel/sentinellog/retrieval/embeddings.py): Local, deterministic, CPU-only TF-IDF embedding abstraction fitted strictly on TRAIN.
5. [`sentinellog.retrieval.engine`](file:///d:/FaultSentinel/sentinellog/retrieval/engine.py): Cosine similarity retrieval engine with deterministic tie-breaking and self-exclusion.
6. [`sentinellog.retrieval.gated`](file:///d:/FaultSentinel/sentinellog/retrieval/gated.py): Integration with Phase 4 selective gate ensuring only escalated traffic triggers retrieval.
7. [`sentinellog.retrieval.phase5_runner`](file:///d:/FaultSentinel/sentinellog/retrieval/phase5_runner.py): End-to-end execution, artifact generation, and diagnostics logging.

---

## 3. Data Leakage Prevention & Train-Only Corpus Policy

### 3.1 Strict TRAIN-Only Invariant
To prevent any subtle evaluation contamination or data leakage:
- **Corpus Split Invariant**: The retrieval corpus is constructed **EXCLUSIVELY** from the `train` partition (`split == "train"`).
- **Test Set Protection (Rule 1)**: `data/test/` remains completely locked and frozen until Phase 7. The retrieval engine programmatically rejects any access to `test.jsonl` via [`guard_no_test_split`](file:///d:/FaultSentinel/sentinellog/scoring/artifacts.py#L21-L46).
- **Calibration Split Protection**: Calibration data is strictly forbidden from entering the retrieval corpus (`calibration_used_for_corpus: false`). Calibration windows are used solely as query inputs to evaluate the gated selective pipeline.

### 3.2 Label Leakage Protection
- Ground-truth anomaly labels are **never** included in the searchable embedding text of chunks or queries.
- In [`build_retrieval_chunk`](file:///d:/FaultSentinel/sentinellog/retrieval/chunking.py#L48-L92) and [`build_query_from_window`](file:///d:/FaultSentinel/sentinellog/retrieval/chunking.py#L115-L141), the searchable text is built solely from observable template tokens: `template_{id}`.
- Ground truth `anomaly_label` is preserved exclusively as a metadata field on corpus chunks for post-hoc research diagnostics; it is inaccessible to the embedding model or similarity search.
- [`guard_no_label_in_text`](file:///d:/FaultSentinel/sentinellog/retrieval/guards.py#L49-L71) and [`guard_query_does_not_contain_labels`](file:///d:/FaultSentinel/sentinellog/retrieval/guards.py#L74-L98) enforce fail-closed runtime validation.

---

## 4. Contextual Chunking & Deterministic Identifiers

### 4.1 Context Unit
The retrieval unit preserves multi-event window context:
- For HDFS: Session-based windows representing complete block lifecycles.
- For BGL: Fixed-size chronological windows representing localized node cluster state.

### 4.2 Deterministic Chunk ID Specification
Each chunk is assigned an immutable, content-derived SHA-256 identifier:
$$\text{chunk\_id} = \text{SHA256}(\text{dataset} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{split} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{source\_window\_id} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{normalized\_text})$$
- Python `hash()` and UUIDs are strictly banned.
- Guarantees 100% bit-for-bit repeatability across executions and environments.

---

## 5. Local Deterministic Embedding Model

### 5.1 Architecture
[`TemplateTfidfEmbeddingModel`](file:///d:/FaultSentinel/sentinellog/retrieval/embeddings.py#L55-L162) provides a lightweight, local, reproducible vector representation:
- **Token Pattern**: `\S+` matching normalized tokens (`template_1`, `template_unknown`).
- **Fitting**: Strict TRAIN-only vocabulary and inverse document frequency (IDF) statistics.
- **Normalization**: $L_2$ vector normalization guarantees that dot product equals cosine similarity.
- **Zero-Norm Safety**: Empty sequences or novel out-of-vocabulary queries safely return an all-zero vector without `NaN`, `Inf`, or division by zero.
- **Independence**: Zero external network requests, zero API keys, sub-second fitting.

### 5.2 Model Metadata & Dimensions
- HDFS Model: Vocabulary dimension $d = 16$, hash `f9d41496e5c81b6e...`
- BGL Model: Vocabulary dimension $d = 19$, hash `3917134514406649...`

---

## 6. Retrieval Engine & Search Policy

### 6.1 Similarity Metric
Cosine similarity is computed between normalized vectors:
$$\text{sim}(q, c) = \frac{q \cdot c}{\|q\|_2 \|c\|_2}$$
With zero-norm handling mapping to $0.0$ similarity.

### 6.2 Top-k Policy & Deterministic Tie-Breaking
- Default $k = 5$ (configurable).
- **Tie-Breaking Convention**: Candidates are sorted strictly by:
  1. `similarity` DESCENDING
  2. `chunk_id` ASCENDING (lexicographical string sort)
  This guarantees that rankings are completely invariant to dictionary hashing or iteration order.

### 6.3 Filtering Policies
1. **Same-Dataset Isolation**: HDFS queries search exclusively over HDFS TRAIN chunks; BGL queries search exclusively over BGL TRAIN chunks.
2. **Self-Retrieval Exclusion**: If the query window originates from TRAIN (e.g., during self-consistency checks), its own `source_window_id` is strictly excluded from candidate results.

---

## 7. Gated Selective Retrieval Integration

The selective gate from Phase 4 directly controls retrieval invocation:
$$\text{Decision}(W) = \begin{cases} \text{AUTO-CLEAR} & \implies \text{Retrieval Bypassed} \\ \text{ESCALATE} & \implies \text{Contextual Retrieval Invoked } (k=5) \end{cases}$$

### Empirical Verification on CALIBRATION Split ($\alpha = 0.05$):
- **HDFS**:
  - Total Windows: 814
  - Auto-Cleared: 775 (95.2%) $\to$ **Zero retrieval overhead**
  - Escalated: 39 (4.8%) $\to$ Contextual retrieval invoked, returning 195 evidence chunks (15 unique)
  - Self-Retrieval Rate: 0.0%
- **BGL**:
  - Total Windows: 100
  - Auto-Cleared: 98 (98.0%) $\to$ **Zero retrieval overhead**
  - Escalated: 2 (2.0%) $\to$ Contextual retrieval invoked, returning 10 evidence chunks (5 unique)
  - Self-Retrieval Rate: 0.0%

---

## 8. Reproducibility Manifests & Artifact Schema

Artifacts are generated in `results/phase5/<dataset>/`:
- `corpus.jsonl`: Line-delimited JSON of all `RetrievalChunk` records.
- `embeddings.npy`: Binary NumPy matrix of shape $(N_{train}, d)$.
- `retrieval_diagnostics.json`: Corpus norms, zero-vector counts, similarity distributions, and duplicate rates.
- `retrieval_manifest.json`: Full provenance including Git commit SHA, Python version, configuration parameters, and SHA-256 artifact hashes:
  - HDFS Corpus SHA-256: `b5b70fdec940e888d6b3d52ca780638dc9c7a25881657371e18c6313e4b8df49`
  - HDFS Embeddings SHA-256: `0bb38c7037ce42cf7729ff2726137eaee1da582e5a4581287b799c105ae27b1d`
  - BGL Corpus SHA-256: `d80e94505949fce1661a1dfff8ad5331fbe63870dc3f753d2b0fe041df44baab`
  - BGL Embeddings SHA-256: `6ff0f8c81bf93944f3817a60e3d7b4fcbf4455cd2cbff6fd95ac071fb4428784`

---

## 9. Research Limitations

1. **Local Deterministic Embeddings vs Pretrained LLM Embeddings**: TF-IDF over template tokens captures structural log template frequency and co-occurrence, but lacks deep natural language semantic understanding. It is chosen for Phase 5 to establish a rigorous, leakage-safe, reproducible baseline without external network dependencies.
2. **Train-Only Historical Availability**: Historical retrieval can only find precedents that occurred in the training split. Novel outage modes unseen during training will retrieve lower-similarity structural neighbors.
3. **Similarity $\neq$ Causality**: Cosine similarity in template space measures behavioral overlap, not root cause. Downstream synthesis in later phases must evaluate whether retrieved evidence is causally relevant.
4. **No LLM Integration in Phase 5**: Phase 5 ends at evidence ranking. Explanation generation and hallucination evaluation belong strictly to future phases.
