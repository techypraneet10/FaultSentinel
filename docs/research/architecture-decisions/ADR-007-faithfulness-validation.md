# ADR-007: Programmatic Faithfulness & Grounding Verification

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
Generative models may insert plausible hallucinations or claim facts not supported by the provided context logs. Human SREs cannot spend time fact-checking each generated sentence during an active outage.

## Problem
How to detect ungrounded statements in the generated explanation before presenting the narrative to the operator?

## Options Considered
1. **Trust-the-Model:** Present LLM output directly without programmatic validation.
2. **LLM-as-a-Judge:** Call another LLM to verify if the first LLM hallucinated (expensive, recursive, non-deterministic).
3. **Deterministic Programmatic Grounding Checker:** Deconstruct the generated narrative into atomic claims, classify claims via fixed taxonomy (`OBSERVATION`, `EVIDENCE`, `CORRELATION`, etc.), and programmatically verify every factual claim against retrieved citations and numeric window features.

## Decision
Adopt **Deterministic Programmatic Faithfulness Checker**.

## Reason
- **Determinism:** Relies on string extraction, citation presence, and numeric validation rather than stochastic second LLMs.
- **Fail-Safe Fallback:** If grounding score is below threshold (e.g. <0.80) or ungrounded claims are detected, the status transitions to `UNSUPPORTED` / `PARTIALLY_SUPPORTED`, and the UI displays a fallback deterministic explanation.
- **Zero Cost:** Programmatic checker executes locally in <2ms with zero external API calls.

## Trade-offs
- Strict lexical and citation requirements can occasionally reject benign, natural prose if citations are formatted improperly.

## Consequences
- Guaranteed detection of citation-missing factual claims.
- Protects operators from acting on ungrounded diagnostic claims.
