# ADR-001: Selective LLM Escalation Architecture

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
Production log streams generate hundreds of thousands of events per minute. Running an LLM (such as Gemini 2.5 Flash) on every raw log line or sliding window is economically prohibitive, operationally slow (high latency), and floods on-call engineers with noisy narratives.

## Problem
How can FaultSentinel leverage generative models for complex incident synthesis without incurring runaway API costs or adding hundreds of milliseconds of latency to routine normal telemetry?

## Options Considered
1. **Always-On LLM Processing:** Send every incoming sliding window to an LLM prompt.
2. **Heuristic Regex Filtering:** Filter logs by static keywords (`ERROR`, `FATAL`) and call LLM for matching lines.
3. **Calibrated Two-Tier Selective Escalation:** Deploy a lightweight, sub-millisecond anomaly scorer (B0/B1/B2) as Tier 1. Filter normal windows deterministically (Auto-Clear) and selectively escalate only statistical anomalies to the LLM tier.

## Decision
Adopt **Two-Tier Selective Escalation**.
The high-throughput, low-parameter ML scorer evaluates every window. Over 94% of windows are classified as routine background noise and auto-cleared in <2ms without network calls. Only windows that breach the calibrated conformal threshold are escalated downstream.

## Reason
1. **Cost Efficiency:** Reduces expensive LLM API invocations by ~95% on evaluated benchmarks.
2. **Speed:** Normal triage latency remains deterministic and instantaneous.
3. **Signal-to-Noise Ratio:** SREs receive LLM explanations only when actual anomalous patterns manifest.

## Trade-offs
- Risk of false clears if the Tier 1 scorer fails to flag a subtle anomaly.
- Requires rigorous calibration to control the miscoverage and escalation rates.

## Consequences
- Phase 1 makes zero external LLM calls.
- LLM spend scales with true system incidents rather than raw telemetry volume.
- Downstream LLM pipelines can afford richer prompt engineering and retrieval because invocation volume is throttled.
