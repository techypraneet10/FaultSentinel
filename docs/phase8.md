# SentinelLog Phase 8: Deterministic Incident Reasoning Engine

## 1. Objective & Research Motivation

Phase 8 introduces the **Deterministic Incident Reasoning Engine** for SentinelLog. Following Phase 4 (conformal selective gate), Phase 5 (TRAIN-only contextual candidate retrieval), Phase 6 (MMR diversity-aware evidence selection), and Phase 7 (cryptographic citation provenance), Phase 8 bridges retrieved evidence and structured incident assessments.

```
RAW LOG WINDOW
      ↓
Phase 4 Selective Gate
      ↓
┌───────────────────────┬────────────────────────────────────────┐
│ AUTO-CLEAR (95-98%)   │ ESCALATE (2-5%)                        │
│ Bypasses Retrieval,   │ 1. Phase 5 Candidate Retrieval (k=5)   │
│ Reranking & Reasoning │ 2. Phase 6 MMR Selection (k=3)         │
│ (Zero LLM/Audit Cost) │ 3. Phase 7 Cryptographic Provenance    │
│                       │ 4. Phase 8 Deterministic Reasoning     │
│                       │ 5. Structured Incident Assessment      │
│                       │ 6. STOP (No LLM generation in Phase 8) │
└───────────────────────┴────────────────────────────────────────┘
```

**Central Research Principle**:
> *Selective escalation indicates that a window deserves deeper scrutiny; it does NOT mean that an incident has definitely occurred. An automated triage system must objectively synthesize anomaly scores, cross-model agreement, evidence sufficiency, and historical corroboration into an inspectable, deterministic assessment before incurring the cost and risk of generative LLM explanation.*

**Absolute Scope Boundary**:
- Phase 8 implements **only deterministic, inspectable reasoning logic**.
- **NO natural-language explanation generation, LLM API calls, prompt engineering, RAG orchestration, web serving, or containerization are present in Phase 8.**
- Phase 9 will consume Phase 8 structured assessments as its deterministic foundation.

---

## 2. Layered Architecture

SentinelLog strictly separates system log analysis into non-overlapping layers:

1. **Detection**: Unsupervised anomaly scoring (Phase 3 B0/B1, Phase 4 B2).
2. **Selective Escalation**: Conformal selective gate establishing guaranteed coverage/error trade-offs (Phase 4).
3. **Evidence Retrieval**: Embedding-based candidate search over historical TRAIN incidents (Phase 5).
4. **Evidence Selection**: MMR diversification compressing candidates into top-$k$ evidence (Phase 6).
5. **Evidence Provenance**: Round-trip source addressability and dual-hash integrity verification (Phase 7).
6. **Deterministic Reasoning**: Rule-based signal aggregation, conflict detection, and assessment derivation (**Phase 8**).
7. **LLM Explanation**: Structured explanation and operator briefing (**Phase 9**).

---

## 3. Inputs & Artifacts Consumed

The reasoning engine operates entirely over committed artifacts from earlier phases:

- **Phase 3**: Frequency baseline score ($B_0$).
- **Phase 4**: Sequential model score ($B_2$), selective gate decision (`AUTO-CLEAR` vs `ESCALATE`), and alpha configuration.
- **Phase 5 & 6**: Candidate count, selected evidence items, similarity relevance scores, MMR selection scores, and redundancy penalties.
- **Phase 7**: Verified citation bundles (`citations.jsonl`), citation IDs, line locations, exact `source_content_hash`, and Drain3 `template_content_hash`.

---

## 4. Outputs & Data Schemas

The engine generates strictly typed, serializable structures defined in [`sentinellog/reasoning/schemas.py`](file:///d:/FaultSentinel/sentinellog/reasoning/schemas.py):

1. [`IncidentAssessment`](file:///d:/FaultSentinel/sentinellog/reasoning/schemas.py#L115-L175):
   - `dataset`: `'hdfs'` or `'bgl'`.
   - `split`: Partition name (`'calibration'`, strictly non-test).
   - `window_id` / `session_id`: Query window identifier.
   - `decision`: Categorical output (`NORMAL`, `SUSPICIOUS`, `INCIDENT`, `INSUFFICIENT_EVIDENCE`).
   - `severity`: Deterministic level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
   - `confidence`: Deterministic support strength in $[0.0, 1.0]$.
   - `signal_summary`: Numerical and categorical signal values.
   - `evidence_contributions`: Evaluated contribution records per citation.
   - `reasoning_trace`: Machine-readable execution trace.
   - `citation_ids`: Ordered list of Phase 7 SHA-256 citation identifiers.
   - `provenance_status`: `'VERIFIED'`, `'INVALID'`, or `'UNAVAILABLE'`.
   - `engine_version`: Engine semantic version (`0.8.0`).
   - `configuration_hash`: SHA-256 hash of canonical configuration.
2. [`EvidenceContribution`](file:///d:/FaultSentinel/sentinellog/reasoning/schemas.py#L60-L76):
   - `citation_id`, `chunk_id`, `relevance_score`, `redundancy_score`, `contribution_type`, `contribution_strength`, `provenance_status`.
3. [`ReasoningTrace`](file:///d:/FaultSentinel/sentinellog/reasoning/schemas.py#L96-L113):
   - `rules_evaluated`, `rules_fired`, `signals`, `evidence_used`, `conflicts`, `final_decision`, `final_severity`.

---

## 5. Decision Taxonomy

The decision taxonomy consists of four deterministic categories:

| Decision | Semantic Meaning | Criteria |
| :--- | :--- | :--- |
| **`NORMAL`** | Window exhibits standard system behavior; no incident indicators. | Auto-cleared by conformal selective gate (`gate_decision == 'AUTO-CLEAR'`). |
| **`SUSPICIOUS`** | Window shows anomalous signals but lacks sufficient historical corroboration or displays conflicting signals. | Escalated, but evidence is partial, relevance is moderate, or signals conflict. |
| **`INCIDENT`** | Corroborated system fault or failure sequence. | Escalated, high anomaly score, valid provenance, and strong supporting evidence. |
| **`INSUFFICIENT_EVIDENCE`** | Cannot corroborate or refute due to missing, low-relevance, or invalid evidence. | Provenance failure, empty evidence set, or evidence relevance below thresholds. |

---

## 6. Severity Taxonomy

Derived from explicit deterministic signals without dataset ground-truth labels:

| Severity | Operational Definition | Deterministic Trigger Rule |
| :--- | :--- | :--- |
| **`CRITICAL`** | Severe anomaly with catastrophic or unknown failure characteristics. | Decision is `INCIDENT` AND (`has_unknown_template == True` OR `anomaly_score >= 2.50`). |
| **`HIGH`** | Corroborated incident with strong historical precedent. | Decision is `INCIDENT` AND `max_relevance >= 0.80` AND `supporting_evidence >= 2`. |
| **`MEDIUM`** | Uncorroborated anomaly, moderate fault, or conflicting signals. | Decision is `SUSPICIOUS` OR moderate `INCIDENT`. |
| **`LOW`** | Routine operational behavior or insufficient evidence. | Decision is `NORMAL` OR `INSUFFICIENT_EVIDENCE`. |

---

## 7. Deterministic Signal Extraction

The [`SignalExtractor`](file:///d:/FaultSentinel/sentinellog/reasoning/signals.py#L22-L186) derives 11 auditable signals:

1. `anomaly_score_strength`: B2 sequential score mapped to `'LOW'` ($<0.50$), `'MEDIUM'` ($[0.50, 1.20)$), or `'HIGH'` ($\ge 1.20$).
2. `selective_escalation_state`: Phase 4 gate output (`'ESCALATE'` vs `'AUTO-CLEAR'`).
3. `baseline_agreement`: Cross-model alignment between frequency baseline ($B_0$) and sequential GRU ($B_2$).
4. `evidence_count`: Number of retrieved and verified citations ($k$).
5. `evidence_relevance`: Mean and max cosine similarity from Phase 5/6.
6. `evidence_diversity`: $1.0 - \text{mean}(\text{redundancy\_penalty})$ from Phase 6 MMR.
7. `repeated_template_behavior`: Ratio of repeated templates to total records in window.
8. `unknown_template_presence`: Boolean flag from Phase 2 preprocessing indicating unseen Drain3 templates.
9. `temporal_concentration`: Log event rate (records per second).
10. `evidence_provenance_validity`: Round-trip Phase 7 verification status (`True`/`False`).
11. `evidence_sufficiency`: Holistic sufficiency assessment (`'SUFFICIENT'`, `'PARTIAL'`, `'INSUFFICIENT'`).

---

## 8. Evidence Sufficiency

Evidence count alone does not constitute sufficient proof. Sufficiency requires:
- **`SUFFICIENT`**: Provenance verified AND $\ge 2$ citations AND mean relevance $\ge 0.50$ AND diversity $\ge 0.20$.
- **`PARTIAL`**: Provenance verified AND $\ge 1$ citation AND mean relevance $\ge 0.40$.
- **`INSUFFICIENT`**: Provenance unverified, $< 1$ citation, or mean relevance $< 0.40$.

---

## 9. Evidence Contribution Types

Each selected citation is assigned a contribution role:
- **`SUPPORTING`**: Valid provenance, relevance $\ge 0.70$. Corroborates the anomaly pattern.
- **`CONTEXTUAL`**: Valid provenance, $0.40 \le \text{relevance} < 0.70$. Provides operational background.
- **`CONTRADICTING`**: Valid provenance, relevance $< 0.40$. Pattern does not match historical incident chunks.
- **`INSUFFICIENT`**: Provenance invalid or unverified. Cannot be safely used for reasoning.

---

## 10. Conflict Handling

Logical conflicts are explicitly identified and recorded in `reasoning_trace.conflicts`:
1. `CONF-001` (`ANOMALY_EVIDENCE_MISMATCH`): High anomaly score but 0 supporting evidence items.
2. `CONF-002` (`CROSS_MODEL_DISAGREEMENT`): Frequency score normal but sequential score high.
3. `CONF-003` (`COUNT_RELEVANCE_DIVERGENCE`): Plentiful candidate chunks retrieved, but all exhibit low similarity.

When high-severity conflicts occur, the engine refuses to force an `INCIDENT` assessment, defaulting transparently to `SUSPICIOUS` with reduced confidence.

---

## 11. Deterministic Rule Engine & Priority Precedence

Rules execute in rigid, non-overlapping priority order:

| Priority | Rule ID | Condition | Output Decision |
| :--- | :--- | :--- | :--- |
| **1** | `RULE-PROV-001` | Provenance unverified or invalid | `INSUFFICIENT_EVIDENCE` |
| **2** | `RULE-INPUT-001` | Guard violation or invalid split | Fails closed (`INVALID_INPUT`) |
| **3** | `RULE-SUFF-001` | Escalated window with `sufficiency == 'INSUFFICIENT'` | `INSUFFICIENT_EVIDENCE` |
| **4** | `RULE-CONF-001` | High-severity conflict between anomaly score & evidence | `SUSPICIOUS` |
| **5** | `RULE-INC-001` | Anomaly `HIGH` AND supporting evidence $\ge 1$ AND sufficiency `SUFFICIENT` | `INCIDENT` |
| **6** | `RULE-SUSP-001` | Escalated window with moderate anomaly or partial evidence | `SUSPICIOUS` |
| **7** | `RULE-NORM-001` | Conformal gate auto-cleared window | `NORMAL` |

---

## 12. Reasoning Confidence (Support Strength)

`confidence` is calculated deterministically via [`ReasoningConfidenceCalculator`](file:///d:/FaultSentinel/sentinellog/reasoning/confidence.py#L18-L82):
$$\text{raw\_confidence} = w_{\text{agree}} \cdot S_{\text{agree}} + w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{div}} \cdot S_{\text{div}} + w_{\text{prov}} \cdot S_{\text{prov}} - \text{penalties}$$
- Default weights: $w_{\text{agree}}=0.30, w_{\text{rel}}=0.30, w_{\text{div}}=0.20, w_{\text{prov}}=0.20$.
- Penalties: Conflict penalty ($-0.25 \times n_{\text{conflicts}}$), insufficiency penalty ($-0.40$).
- Clamped to $[0.05, 0.98]$.

**Notice**: This metric reflects deterministic corroboration strength. It is **not** a calibrated frequentist or Bayesian probability of real-world correctness.

---

## 13. Provenance Gate & Failure Closed

Before reasoning commences, [`validate_provenance_gate`](file:///d:/FaultSentinel/sentinellog/reasoning/validation.py#L58-L108) verifies:
- Citation bundle is present.
- `all_verified == True`.
- Citation IDs, line coordinates, and dual hashes match deterministic derivation.
- If provenance fails, `RULE-PROV-001` fires immediately, setting `provenance_status = "INVALID"`, `decision = "INSUFFICIENT_EVIDENCE"`, and `confidence = 0.05`.

---

## 14. Configuration & Hashing

Centralized in [`configs/phase8.yaml`](file:///d:/FaultSentinel/configs/phase8.yaml).
- Serialized canonically to JSON and hashed via SHA-256 (`configuration_hash: 57e370a7c64a...`).
- Embedded in every manifest and assessment for reproducibility.

---

## 15. Research Integrity & Leakage Prevention

- **Test Set Protection (Rule 1)**: `data/test/` is completely unreferenced. `test_used: false` is verified across all manifests.
- **Label Leakage Protection**: [`validate_no_label_leakage`](file:///d:/FaultSentinel/sentinellog/reasoning/validation.py#L25-L45) recursively rejects any data structure containing `anomaly_label`, `is_anomaly`, `ground_truth`, or `target`.

---

## 16. Experimental Results & Diagnostics

Executed over the 39 HDFS and 2 BGL escalated windows from Phase 6/7:

| Dataset | Total Assessed | Decision Distribution | Severity Distribution | Provenance Status | Conflict Rate | Avg Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HDFS** | 39 | `INCIDENT`: 33, `SUSPICIOUS`: 6 | `HIGH`: 27, `CRITICAL`: 6, `LOW`: 6 | `VERIFIED`: 39 (100%) | 0.0% | 0.9043 |
| **BGL** | 2 | `INSUFFICIENT_EVIDENCE`: 2 | `LOW`: 2 | `VERIFIED`: 2 (100%) | 100.0% | 0.0500 |

### BGL Insight
For BGL, the 2 escalated windows had high sequential anomaly scores, but the historical TRAIN retrieval corpus contained near-zero relevant matches (average relevance = $0.0240$).
The reasoning engine correctly recognized the lack of corroborating evidence, flagged an explicit conflict, and refused to declare `INCIDENT`, outputting `INSUFFICIENT_EVIDENCE`.

---

## 17. Deterministic Ablation Analysis

Executed across four controlled variants:
1. **Ablation A (Single Strongest Signal)**: Ignores cross-model agreement and repetition density.
2. **Ablation B (Relevance Only)**: Disables diversity penalty in sufficiency calculation.
3. **Ablation C (Conflict Ignored)**: Bypasses `RULE-CONF-001`, showing that BGL confidence rises to 0.2873 when conflicts are unpenalized.
4. **Ablation D (Sufficiency Disabled)**: Forces BGL into `SUSPICIOUS` (severity `MEDIUM`) by assuming non-empty evidence is sufficient, demonstrating the essential protective role of evidence sufficiency.

---

## 18. Phase 9 Interface

Phase 9 (LLM Explanation & Operator Briefing) will consume Phase 8 assessments through the programmatic interface:

```python
from sentinellog.reasoning.engine import IncidentReasoningEngine

engine = IncidentReasoningEngine(config_path="configs/phase8.yaml")
result = engine.assess(
    window=query_window,
    anomaly_score=b2_score,
    gate_decision="ESCALATE",
    citation_bundle=phase7_citation_bundle,
    b0_score=b0_score,
)

assessment = result.assessment
# Phase 9 consumes:
# assessment.decision                 ('INCIDENT', 'SUSPICIOUS', etc.)
# assessment.severity                 ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
# assessment.confidence               (0.0 to 1.0)
# assessment.citation_ids             (Verified Phase 7 citation hashes)
# assessment.evidence_contributions   (Classified citation roles)
# assessment.reasoning_trace          (Audit trail of fired rules and conflicts)
```

---

## 19. Limitations & Explicit Scope Boundaries

1. **Deterministic Reasoning is NOT Ground Truth**: Assessments reflect rule-based synthesis of historical telemetry, not infallible ground reality.
2. **Confidence is Support Strength**: Not a frequentist p-value or calibrated posterior probability.
3. **Provenance Verifies Addressability, Not Semantic Truth**: A valid citation proves where a record came from and that it has not been modified; it does not guarantee that historical log messages were truthful.
4. **No LLM in Phase 8**: Phase 8 contains zero natural-language text generation.
