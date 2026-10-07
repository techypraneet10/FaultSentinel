# Evidence Graph & Provenance Topology

## Overview
The **Evidence Graph** renders an interactive visual representation of the complete provenance chain supporting an automated incident decision.

## Node Taxonomy
The graph models 10 distinct architectural node types:
1. `Incident`: The high-level incident context.
2. `Window`: The sliding log window evaluated.
3. `Score`: The continuous anomaly signal produced by the model.
4. `Decision`: The conformal threshold gate evaluation (`ESCALATE` or `AUTO_CLEAR`).
5. `Retrieved Chunk`: The candidate historical chunks retrieved from the train vector index.
6. `Evidence`: The MMR-diversified evidence set selected for context.
7. `Provenance`: The cryptographic hash verification binding chunks to raw logs.
8. `Reasoning Claim`: The authoritative diagnosis produced by the deterministic rules engine.
9. `LLM Claim`: The atomic assertions generated downstream by the language model.
10. `Citation`: The machine-verifiable citations anchoring LLM claims to source log coordinates.
11. `Source Log`: The underlying physical log record in the immutable train split.

## Integrity Principle (Rule 7.3)
Every node and edge is generated directly from recorded execution provenance. If a relationship cannot be cryptographically proven, the edge is rendered as `UNRESOLVED` rather than hallucinated or inferred.
