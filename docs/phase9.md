# Phase 9: LLM Explanation & Orchestration Layer

## 1. Objective

Phase 9 implements the **LLM Explanation & Orchestration Layer** for SentinelLog ("Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs").

In this architecture:
- The LLM is an **EXPLANATION COMPONENT**.
- The LLM is **NOT** the primary anomaly detector.
- The LLM is **NOT** the selective gate (Phase 4).
- The LLM is **NOT** the provenance verifier (Phase 7).
- The LLM is **NOT** the deterministic incident classifier (Phase 8).
- The LLM **NEVER** overrides Phase 8's deterministic triage decision or severity.
- The LLM **NEVER** manufactures citations or invents unsupported evidence.
- The LLM **NEVER** converts uncertainty into false certainty.

Phase 9 investigates:
> *"Can an LLM produce a useful incident explanation when it is constrained by deterministic reasoning, verified evidence, and exact citations?"*

It explicitly does **NOT** ask whether an LLM can independently detect anomalies from raw logs.

---

## 2. End-to-End Pipeline Architecture

```
Raw Logs
   ↓
Phase 2: Leakage-Safe Data Pipeline (Chronological Splits, Drain3 Templates)
   ↓
Phase 3: Classical Baselines (B0 Token Frequency Baseline)
   ↓
Phase 4: Sequential Scoring + Conformal Selective Gate (B2 GRU, Risk-Controlled Escalation)
   ↓
Phase 5: Dense Retrieval Infrastructure (Historical Train Chunks, Embeddings)
   ↓
Phase 6: MMR Evidence Selection (Relevance & Diversity Trade-Off)
   ↓
Phase 7: Verified Provenance Engine (Dual-Hash Content Fingerprints & Coordinates)
   ↓
Phase 8: Deterministic Incident Reasoning (Decision, Severity, Conflict & Sufficiency Rules)
   ↓
PHASE 9: LLM EXPLANATION & ORCHESTRATION
   ├── Context Construction (Bounded, Label-Leakage Sanitized)
   ├── Versioned Prompt Builder (Prompt Injection Defenses)
   ├── Safe LLM Provider (Offline Mock & External API Abstraction)
   ├── Structured Output Parser (Strict JSON Schema)
   ├── Multi-Stage Output Validator:
   │     ├── Decision & Severity Immutability Check
   │     ├── Citation Integrity & Provenance Check
   │     ├── Claim Extraction & Taxonomy Enforcement
   │     └── Deterministic Faithfulness & Grounding Check
   ├── Deterministic Fallback & Abstention Handler
   └── Auditable Artifact Serializer
```

---

## 3. Phase 9 Input Contract

The Phase 9 `ExplanationOrchestrator` consumes:
1. **Phase 8 Outputs:**
   - `IncidentAssessment`: authoritative deterministic decision (`NORMAL`, `SUSPICIOUS`, `INCIDENT`, `INSUFFICIENT_EVIDENCE`), severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), confidence score $[0.0, 1.0]$, signal summary, and evidence contribution classifications.
   - `ReasoningTrace`: evaluated and fired deterministic rules, numeric signals, and conflict records.
2. **Phase 7 Provenance:**
   - `CitationBundle`: verified list of `Citation` records with source coordinates (file, line ranges, record count, session/block ID), dual-hash content fingerprints (`source_content_hash`, `template_content_hash`), and verification status (`all_verified: True`).
3. **Phase 6 Selections:**
   - MMR rank order, retrieval scores, and MMR selection diversity scores.
4. **Phase 4 & 3 Signals:**
   - B2 sequential anomaly score, B0 baseline score, and cross-model agreement.

Phase 9 does not recompute or modify any upstream phase outputs.

---

## 4. Provider Abstraction

All LLM invocations occur strictly behind the `BaseLLMProvider` interface:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> LLMResponse:
        pass
```

Two concrete implementations are provided:
- **`MockLLMProvider`**: A fully deterministic, zero-network mock provider used for unit tests, CI, and offline verification. Supports configurable error injection modes (`invalid_citation`, `missing_citation`, `unsupported_claim`, `changed_decision`, `changed_severity`, `malformed_json`, `numeric_mismatch`, `prompt_injection`, `timeout`, `provider_error`, `empty_response`).
- **`OpenAILLMProvider`**: A production provider that connects to external completion APIs without third-party dependencies, reading credentials exclusively from the `SENTINELLOG_LLM_API_KEY` environment variable.

The `SafeLLMClient` wraps providers to enforce bounded retries (`max_retries: 2`), timeout management, and runtime token/latency telemetry tracking.

---

## 5. Prompt Architecture

Prompt versioning follows Rule 3 and Rule 55:
- **Prompt Version:** `v1.0` (`SENTINELLOG_EXPLANATION_PROMPT_V1`)
- **System Prompt:** Explicitly informs the model of its subordinate explanation role, mandates decision immutability, forbids citation invention, establishes untrusted data boundaries, and requires structured JSON.
- **Delimited Sections:**
  1. `SECTION 1: DETERMINISTIC ASSESSMENT (PHASE 8)`: authoritative decision, severity, confidence, sufficiency, and rules fired.
  2. `SECTION 2: VERIFIED EVIDENCE & CITATIONS (PHASE 7)`: citation IDs, source coordinates, relevance scores, and bounded log excerpts clearly marked as untrusted data.
  3. `SECTION 3: REASONING SIGNALS & CONFLICTS`: B2/B0 scores, baseline agreement, and detected conflicts.
  4. `SECTION 4: REQUIRED OUTPUT SCHEMA`: rigid JSON schema specification.

---

## 6. Context Construction & Leakage Prevention

`ExplanationContextBuilder` enforces strict guardrails:
1. **Rule 1 Split Guardrail:** The frozen `test` partition is unconditionally rejected. Any attempt to build context on `test` raises `InvalidSplitError`.
2. **Rule 34 Label Leakage Prevention:** Context is scanned recursively for forbidden evaluation keys (`is_anomaly`, `anomaly_label`, `ground_truth`, `target`, `label`, `test_label`, `unmapped_label`, `hidden_*`). Detecting any such field raises `LabelLeakageError`.
3. **Bounded Context:** Raw log excerpts are bounded to 5 lines and 400 characters per citation to prevent token blowup.

---

## 7. Citation Strategy

The LLM is constrained to cite only existing Phase 7 citation IDs:
- Citations must match the exact 64-character SHA-256 fingerprint or assigned `[CIT-...]` identifier from the current window's `CitationBundle`.
- Fabricated citation IDs, nonexistent line coordinates, or citations belonging to a different query window are detected and rejected.
- **Citation Precision Metric:**
  $$\text{citation\_precision} = \frac{\text{valid cited evidence references}}{\text{total cited evidence references}}$$

---

## 8. Claim Validation & Taxonomy

Every atomic statement in the generated explanation is parsed into `ExplanationClaim` and classified into a fixed vocabulary:
- **`OBSERVATION`**: Directly observed pattern in the query window (factual; requires citation).
- **`EVIDENCE`**: Historical failure pattern retrieved from verified citations (factual; requires citation).
- **`CORRELATION`**: Relationship between current window behavior and cited historical events (factual; requires citation).
- **`INTERPRETATION`**: Reasoning synthesis explaining why the deterministic decision was reached (structural; cites Phase 8 metadata).
- **`UNCERTAINTY`**: Boundary of what available evidence cannot establish.
- **`RECOMMENDATION`**: Actionable suggestion for the on-call engineer (must not be presented as factual evidence).

Unsupported causal assertions (e.g., "caused by", "crashed because") are flagged if unbacked by evidence.

---

## 9. Programmatic Faithfulness & Grounding Checker

`FaithfulnessChecker` provides a deterministic grounding audit (no second LLM judge):
1. **Citation Grounding:** Confirms every factual claim references valid citation IDs in the current bundle.
2. **Lexical Overlap:** Computes token overlap between claim content words and cited log template sequences.
3. **Numeric Consistency (Rule 19):** Extracts all numeric values from claims and verifies them against trusted Phase 8 signals, Phase 7 coordinates, or common indices. Altered scores or invented counts are flagged.
4. **Contradiction Detection:** In `INSUFFICIENT_EVIDENCE` windows, flags any claim asserting confirmed incidents or verified attacks.
5. **Citation Coverage Metric (Rule 16):**
  $$\text{citation\_coverage} = \frac{\text{supported factual claims}}{\text{total factual claims}}$$
6. **Faithfulness Status Taxonomy:**
  - `VERIFIED`: Coverage $\ge 0.50$, zero contradictions, numeric checks passed.
  - `PARTIALLY_SUPPORTED`: Coverage $> 0.0$ and $< 0.50$, or minor unsupported claims.
  - `UNSUPPORTED`: Zero factual claims supported.
  - `INVALID`: Contradiction detected or invalid provenance.
  - `NOT_EVALUATED`: Explanation was abstained prior to check.

---

## 10. Decision Immutability

Phase 8 is authoritative for:
- Incident Decision (`NORMAL`, `SUSPICIOUS`, `INCIDENT`, `INSUFFICIENT_EVIDENCE`)
- Severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- Reasoning Confidence
- Evidence Sufficiency State

If the LLM outputs a conflicting decision or severity:
- `ExplanationValidator` marks `is_valid = False` and records a decision/severity immutability violation.
- The orchestrator falls back to `ABSTAINED` status via `FallbackHandler`.
- Under no circumstances is the deterministic result modified to match the LLM.

---

## 11. Abstention & Fallback Behavior

When:
- Provenance verification fails (`provenance_status != 'VERIFIED'`),
- Citation validation fails,
- JSON parsing or schema validation fails,
- Decision or severity immutability is violated,
- LLM provider errors or times out,
- Citation coverage falls below the required threshold,

the system triggers deterministic fallback:
- `explanation_status = ExplanationStatus.ABSTAINED` (or `VALIDATION_FAILED`, `PROVIDER_ERROR`)
- `abstained = True`
- `abstention_reason = "<explicit trigger>"`
- **Preserved Invariants:** Phase 8 decision, severity, confidence, and citation bundle coordinates are preserved exactly.

---

## 12. Prompt Injection Defense

Retrieved logs are untrusted data and may contain adversarial instruction payloads:
- System instructions explicitly designate all log texts as untrusted data.
- User prompt places log excerpts inside explicit delimiter blocks (`Log Excerpt (Untrusted Data): """..."""`).
- Instructions prohibit the model from altering role, overriding triage decisions, or executing commands embedded in logs.
- Dedicated unit tests verify that injection payloads do not hijack explanation synthesis.

---

## 13. Configuration

Stored in `configs/phase9.yaml`:
```yaml
provider:
  type: "mock"
  model: "sentinellog-mock-v1"
  mock_mode: "default"
  api_key_env: "SENTINELLOG_LLM_API_KEY"

temperature: 0.0
max_tokens: 1000

client:
  timeout: 30.0
  max_retries: 2

prompt_version: "v1.0"

citation_requirements:
  strict_provenance: true
  min_citations_for_factual: 1

faithfulness_thresholds:
  min_coverage: 0.50
  min_lexical_overlap: 0.05

claim_limits:
  max_claims: 10

token_limits:
  max_input_tokens: 4000
  max_output_tokens: 1000

paths:
  phase7_dir: "results/phase7"
  phase8_dir: "results/phase8"
  output_dir: "results/phase9"
```
The configuration has a deterministic SHA-256 fingerprint: `compute_configuration_hash(config)`.

---

## 14. Security & Privacy

- **No Secrets in Code or Config:** API keys are never stored in source code, YAML configurations, or artifacts.
- **Environment Isolation:** Keys are loaded via `SENTINELLOG_LLM_API_KEY`.
- **Zero Secret Logging:** Error logs sanitize authorization headers and connection URLs.
- **Safe Telemetry:** Runtime token counts and latencies are recorded without persisting raw credentials.

---

## 15. Engineering Diagnostics & Metrics

Reported in `metrics.json` (Rule 40):
- `total_attempted`: Total explanation opportunities.
- `successful_generations`: Completed explanations.
- `abstentions`: Abstained explanations.
- `provider_failures`: Provider errors.
- `validation_failures`: Rejection by validator.
- `decision_consistency_failures`: Contradictory decision attempts.
- `citation_coverage`: Supported factual claims / total factual claims.
- `citation_precision`: Valid cited references / total cited references.
- `unsupported_claim_rate`: $1.0 - \text{citation\_coverage}$.
- `faithfulness_distribution`: Breakdown of `VERIFIED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `INVALID`.
- `mean_latency_ms`: Average provider call latency.
- `total_tokens`: Token consumption.
- `human_evaluation = NOT_AVAILABLE`: Rule 41 explicitly forbids fabricating human evaluation scores.

---

## 16. Deterministic Mock Provider

The `MockLLMProvider` operates completely offline and produces bitwise deterministic responses matching Phase 8 assessments and Phase 7 citations. It is used for all automated CI runs and regression tests.

---

## 17. Real LLM Experiment Protocol

When running experiments with external models:
1. Set `SENTINELLOG_LLM_API_KEY` in environment.
2. Update `configs/phase9.yaml` to `provider.type: "openai"` or `"external"`.
3. Set `temperature: 0.0`.
4. Execute `python -m sentinellog.explanation.phase9_runner`.
5. Every experiment run automatically records:
   - Provider name, model name, prompt version.
   - Configuration SHA-256 hash.
   - Input artifact hashes.
   - Git commit SHA.
   - Token usage and latencies.

---

## 18. Limitations

1. **Not Hallucination-Free:** Phase 9 does not guarantee semantic truth or eliminate hallucinations. The faithfulness checker is an empirical grounding check that tests citation existence and lexical overlap.
2. **Citation Validation Scope:** Citation validation verifies that cited chunk IDs exist, match Phase 7 hashes, and belong to the window; it does not prove that the cited log message semantically causes the incident.
3. **Empirical Lexical Overlap:** Grounding relies on token overlap with templates; complex linguistic inferences require downstream human review.
4. **Deterministic Subordination:** The LLM is an explanation layer only. Incident classification is governed by Phase 8.

---

## 19. Phase 10 Interface

Phase 10 (Serving / Evaluation / Human-in-the-Loop Triage) can consume the complete `ExplanationResult`:
```python
result = orchestrator.explain(
    assessment=assessment,
    citation_bundle=citation_bundle,
    dataset=dataset,
    split=split,
)
```
Fields exposed for Phase 10:
- `explanation_id`: Unique traceable ID.
- `incident_decision`: Authoritative Phase 8 decision (`INCIDENT`, `SUSPICIOUS`, etc.).
- `severity`: Authoritative Phase 8 severity (`HIGH`, `MEDIUM`, etc.).
- `reasoning_confidence`: Phase 8 confidence score.
- `summary`: High-level incident summary.
- `explanation`: Full formatted explanation narrative.
- `claims`: Granular claim objects with citation IDs and support status.
- `citations`: Verified evidence citations with line coordinates and provenance status.
- `uncertainties`: Explicit boundaries of what logs cannot prove.
- `recommended_action`: Next-step suggestion.
- `provenance_status`: Phase 7 verification status (`VERIFIED`).
- `citation_validation_status`: Citation validity (`VALID`).
- `faithfulness_status`: Grounding status (`VERIFIED`, `PARTIALLY_SUPPORTED`).
- `abstained`: Boolean flag indicating whether the narrative was abstained.
- `abstention_reason`: Reason for abstention if applicable.
