# ADR-005: Maximal Marginal Relevance (MMR) for Evidence Diversification

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
In large distributed system outages (e.g., cascading connection timeouts), vector search returns dozens of near-identical log snippets from the same component or thread, crowding out orthogonal symptoms.

## Problem
How to provide an LLM context window with high-relevance evidence without drowning it in redundant log lines?

## Options Considered
1. **Top-K Dense Retrieval:** Simply select the top $K$ items with highest cosine similarity.
2. **Cluster Centroid Selection:** Run K-Means on the retrieved embedding vectors.
3. **Maximal Marginal Relevance (MMR):** Greedily select chunks balancing query relevance against similarity to already selected chunks:
   $$\text{MMR} = \operatorname{argmax}_{d \in R \setminus S} \left[ \lambda \operatorname{Sim}_1(d, q) - (1-\lambda) \max_{d_j \in S} \operatorname{Sim}_2(d, d_j) \right]$$

## Decision
Adopt **MMR Selection with $\lambda = 0.5$**.

## Reason
- MMR eliminates near-duplicate log clusters while preserving distinct failure modes (e.g., both the database disconnect and the subsequent upstream threadpool starvation).
- Bounds prompt token overhead while maximizing symptom coverage.

## Trade-offs
- Slight quadratic complexity over the retrieved candidate set ($O(K^2)$ where $K \approx 10-20$), which is negligible (<1ms).

## Consequences
- Prompt context contains diverse, informative evidence chunks.
- Evidence counts per incident are compact (typically 2-4 distinct chunks).
