# FaultSentinel Research Experiment Record Template

```markdown
# Experiment Record: [EXP-YYYYMMDD-NAME]

## 1. Metadata
- **Experiment ID:** EXP-[ID]
- **Date:** YYYY-MM-DD
- **Author:** [Name / Role]
- **Git Commit:** [SHA-256 / short hash]
- **Dataset:** [HDFS / BGL / Synthetic]
- **Pipeline Version:** v1.1-conformal-grounded
- **Configuration Hash:** [SHA-256]

---

## 2. Research Question
[State the exact empirical question this experiment investigates. Avoid open-ended or non-falsifiable questions.]

## 3. Hypothesis
[State the directional, measurable hypothesis to test.]

## 4. Dataset & Split Specification
- **Dataset:** [HDFS / BGL]
- **Split:** Strictly Chronological (TRAIN / CALIBRATION / TEST)
- **Protected Test Set Notice:** [Rule 1 Compliance Check: Is test/ protected and unaccessed?]
- **Sample Count:** N = [Count] windows

## 5. System Configuration & Hyperparameters
```json
{
  "random_seed": 42,
  "nominal_alpha": 0.05,
  "scorer": "B2_LSTM_Ensemble",
  "scorer_params_count": 894200,
  "retrieval_k": 5,
  "mmr_lambda": 0.5,
  "faithfulness_min_grounding": 0.80
}
```

## 6. Experimental Method
1. [Step 1: Ingestion & Parsing]
2. [Step 2: Scoring & Conformal Gating]
3. [Step 3: Selective Retrieval & Provenance]
4. [Step 4: Deterministic Reasoning & Faithfulness Verification]

## 7. Measured Metrics
- **Selective Escalation Rate:** [%]
- **Empirical Coverage ($1 - \text{escalation}$):** [%]
- **Precision / Recall / F1:**
- **Inference Latency (p50 / p95 / p99):** [ms]
- **Faithfulness Grounding Pass Rate:** [%]

## 8. Expected Result
[Specific numerical predictions prior to execution.]

## 9. Observed Result
[Raw, unedited execution results from artifact outputs.]

## 10. Unexpected Findings
[Discrepancies, edge-case anomalies, or distribution shifts.]

## 11. Scientific Interpretation
[Defensible interpretation grounded directly in the observed metrics.]

## 12. Known Limitations & Threats to Validity
- Temporal drift / non-stationarity
- Hardware / latency profile
- Label sparsity or class imbalance

## 13. Release Decision
- [ ] APPROVED FOR STAGING
- [ ] CALIBRATION REVIEW REQUIRED
- [ ] REJECTED / RE-BENCHMARK

## 14. Next Step
[Concrete engineering action following this experiment.]
```
