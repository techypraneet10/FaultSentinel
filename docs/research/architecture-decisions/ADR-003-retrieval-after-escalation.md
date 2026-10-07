# ADR-003: Retrieval Triggered Strictly After Escalation

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
Dense vector indexing (FAISS/BM25) over millions of historical log chunks incurs vector similarity computation overhead and memory footprint.

## Problem
Should vector retrieval run for every ingested log window, or only when an anomalous event is confirmed?

## Options Considered
1. **Continuous Pre-Retrieval:** Query the vector index for every window concurrently with scoring.
2. **Selective Post-Escalation Retrieval:** Gated execution. Only if the window breaches the conformal threshold ($\text{score} > \tau_\alpha$) do we query the vector index for historical precedents.

## Decision
Adopt **Selective Post-Escalation Retrieval**.

## Reason
1. **Computational Efficiency:** 95% of routine windows never trigger index search or vector embeddings.
2. **Resource Isolation:** Memory bandwidth and index search locks remain free for active incident analysis.
3. **Decoupled Architecture:** Scorer and Retriever operate sequentially, allowing fast-path rejection.

## Trade-offs
- Slight latency penalty (+15-40ms) on escalated windows because retrieval cannot be pipelined ahead of scoring.

## Consequences
- Fast-path triage remains sub-millisecond.
- Heavy historical index lookup occurs solely when human or LLM escalation is guaranteed.
