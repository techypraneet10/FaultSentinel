# ADR-004: Deterministic Reasoning Precedes and Governs LLM Explanation

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
LLMs are non-deterministic and can produce persuasive but inaccurate incident root causes, invent error classifications, or hallucinate severity ratings.

## Problem
How to ensure that automated incident assessments (severity, category, triage action) remain deterministic, testable, and reliable even if the LLM produces a flawed narrative or fails entirely?

## Options Considered
1. **LLM as the Deciding Agent:** Feed raw logs into an LLM prompt and ask it to output severity, category, and root cause in JSON.
2. **Deterministic Rules with LLM as Downstream Explainer:** Use programmatic, rule-based expert logic (Phase 8 deterministic reasoning) as the authoritative decision-maker. The LLM only synthesizes human-readable explanations downstream, bound strictly by the deterministic assessment.

## Decision
Adopt **Deterministic Reasoning as Authoritative Tier**.
The decision (`ESCALATE`, `AUTO_CLEAR`, `INSUFFICIENT_EVIDENCE`), severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and root cause taxonomy are locked deterministically by the rules engine before any LLM prompt is executed. The LLM cannot override the machine decision.

## Reason
- **Auditability:** Triage decisions can be reproduced in unit tests without network calls or stochastic variance.
- **Fail-Safe Operation:** If the LLM times out or crashes, the system gracefully returns the deterministic decision with zero data loss.
- **Guardrails:** Prevents stochastic models from demoting critical outages or escalating non-issues.

## Trade-offs
- Deterministic rule sets require initial domain rule curation.

## Consequences
- The LLM's role is strictly explanatory, never authoritative.
- Unit and integration tests verify incident triage with 100% deterministic reproducibility.
