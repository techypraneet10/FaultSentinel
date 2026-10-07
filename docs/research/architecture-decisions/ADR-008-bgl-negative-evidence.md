# ADR-008: BGL Negative Evidence & Insufficient Evidence State

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
In diverse supercomputing logs like the BlueGene/L (BGL) dataset, novel anomaly types occasionally have zero historical precedents in the training corpus. When vector retrieval returns zero relevant matches, standard RAG pipelines either fail or synthesize plausible explanations out of thin air.

## Problem
How should the system behave when an anomaly score breaches the conformal threshold, but retrieval yields zero historical matches?

## Options Considered
1. **Force Synthesis:** Pass the empty evidence to the LLM anyway and ask it to speculate.
2. **Crash / Internal Error:** Throw an exception indicating missing data.
3. **Explicit Insufficient Evidence State:** Emit an authoritative `INSUFFICIENT_EVIDENCE` decision with low severity. Inform the operator that a statistical anomaly occurred, but no historical precedent exists to confirm a known failure signature.

## Decision
Adopt **Authoritative `INSUFFICIENT_EVIDENCE` State**.

## Reason
- **Intellectual Honesty:** Acknowledging the absence of evidence is safer than inventing a fictitious root cause.
- **Operator Trust:** SREs know immediately that they are investigating a novel or unprecedented log signature.
- **Fail-Safe Triage:** Prevents catastrophic false alarms based on zero evidence.

## Trade-offs
- The incident cannot be automatically diagnosed until an operator inspects it or historical precedents are updated.

## Consequences
- BGL slice with 0 train matches reliably exercises this path.
- The pipeline never fabricates root causes under sparse evidence.
