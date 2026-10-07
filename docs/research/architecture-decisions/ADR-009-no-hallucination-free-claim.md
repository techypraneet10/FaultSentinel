# ADR-009: Elimination of "Hallucination-Free" Marketing Claims

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
Promotional AI claims asserting systems are "100% hallucination-free" or "eliminate all false positives" are technically false, undermine engineering credibility, and misrepresent statistical reality.

## Problem
How should FaultSentinel communicate its reliability and grounding mechanisms accurately without misleading users or reviewers?

## Options Considered
1. **Commercial Hyperbole:** Claim "FaultSentinel eliminates hallucinations completely."
2. **Defensible Scientific Framing:** State measured empirical results precisely: "Programmatic citation validation achieved 100% claim coverage on the validated evaluation slice. Unverified claims trigger deterministic fallbacks."

## Decision
Adopt **Defensible Scientific Framing**.
Prohibit claims of "hallucination-free", "zero false positives", or "fully autonomous AGI" in codebase documentation, UI banners, and research notes.

## Reason
- **Scientific Integrity (Rule 7):** Generative language models are inherently probabilistic; programmatic grounding bounds and detects ungrounded claims, but cannot alter the fundamental nature of autoregressive token prediction.
- **Auditor Credibility:** Enterprise SRE leads and academic researchers demand precision over marketing hyperbole.

## Trade-offs
- Less flashy marketing copy.

## Consequences
- The system is positioned as an auditable, calibrated incident investigation workbench.
- Faithfulness is reported as a quantitative grounding score and verification status.
