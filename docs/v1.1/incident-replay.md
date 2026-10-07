# Incident Replay Lab

## Overview
The **Incident Replay Lab** enables SRE engineers, researchers, and recruiters to inspect the step-by-step decision sequence of any historical incident or routine window without re-executing inference.

## Replay Principle
Replay is an **observational** layer over stored execution data. It does not re-score, retrain, or retune models.

## Pipeline Stages
The replay engine visualizes 11 chronological stages:
1. `01_INGEST`: Ingest raw log lines and strip sensitive identifiers.
2. `02_PARSE`: Drain3 template extraction and structured token extraction.
3. `03_WINDOW`: Fixed-size sliding window aggregation ($W=50$).
4. `04_SCORE`: Low-parameter anomaly scoring ($B0 / B1 / B2$).
5. `05_CONFORMAL`: Split conformal decision gate against calibrated threshold $\tau_\alpha$.
6. `06_RETRIEVE`: Dense vector search across training split index ($k=5$).
7. `07_MMR`: Maximal Marginal Relevance evidence selection ($\lambda=0.5$).
8. `08_PROVENANCE`: Dual-hash source and template cryptographic verification.
9. `09_REASONING`: Authoritative deterministic classification and severity assignment.
10. `10_LLM`: Downstream LLM explanation synthesis.
11. `11_VERIFY`: Programmatic claim citation grounding and faithfulness verification.

## Controls & Speed
- `[FIRST]`, `[PREVIOUS]`, `[PLAY]`, `[PAUSE]`, `[NEXT]`, `[LAST]`
- Playback speeds: `0.5x`, `1.0x`, `2.0x`

## Counterfactual Analysis
Engineers can simulate counterfactual scores (e.g. "What if the anomaly score was 0.95 instead of 1.37?") to observe how the decision would shift across the conformal boundary.
Counterfactual states are prominently marked with `COUNTERFACTUAL` badges to prevent confusion with actual production decisions.
