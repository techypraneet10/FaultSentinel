# FaultSentinel

### Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis

FaultSentinel is an AI-assisted incident intelligence platform designed to identify anomalous system-log windows, selectively escalate high-risk events, retrieve historical evidence, perform deterministic incident reasoning, and generate evidence-grounded explanations.

Instead of sending every log window to an expensive LLM, FaultSentinel introduces a **calibrated selective escalation layer** that decides which events actually require deeper investigation.

The system combines:

**Log Parsing → Anomaly Detection → Conformal Risk Control → Selective Escalation → Historical Retrieval → Evidence Selection → Provenance Verification → Deterministic Reasoning → LLM Explanation → Faithfulness Validation**

---

## Why FaultSentinel?

Modern observability systems can generate enormous volumes of logs.

A naive AI-based monitoring system could send every log window to an LLM:

```text
Millions of Logs
      ↓
      LLM
      ↓
Expensive + Slow + Difficult to Audit
