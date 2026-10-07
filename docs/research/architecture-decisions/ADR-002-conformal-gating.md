# ADR-002: Conformal Gating Over Heuristic Thresholding

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
Anomaly detectors output raw scores (e.g., reconstruction errors or sequence log-likelihoods). Setting an operational threshold arbitrarily (e.g., "score > 0.8") lacks statistical justification and causes unpredictable false alarm rates as models or input densities change.

## Problem
How to set an anomaly escalation boundary that provides rigorous statistical bounds on escalation volume while respecting finite calibration sample sizes?

## Options Considered
1. **Ad-Hoc Manual Thresholding:** SREs tune a threshold constant manually based on intuition.
2. **Standard Normal / Z-score Assumption:** Assume anomaly scores follow a Gaussian distribution and set threshold at $\mu + 3\sigma$.
3. **Inductive Split Conformal Prediction:** Use a dedicated, chronological calibration set to compute exact order-statistic quantiles: $k = \lceil (n+1)(1-\alpha) \rceil$, guaranteeing finite-sample tail bounds under exchangeability.

## Decision
Adopt **Split Conformal Prediction** with exact finite-sample order-statistic thresholding:
$$\tau_\alpha = s_{(\lceil (n+1)(1-\alpha) \rceil)}$$

## Reason
- Finite-sample guarantee: upper-tail escalation rate is mathematically bounded by $\alpha$ over calibration exchangeability.
- No distributional assumptions (distribution-free): does not assume Gaussianity or bell curves.
- Traceable and reproducible: the threshold $\hat{q}$ is derived deterministically from the calibration split.

## Trade-offs
- Conformal guarantees bound score-tail escalation, not anomaly label miscoverage (since labels are unobserved in unsupervised triage).
- Temporal non-stationarity can induce drift, requiring monitoring.

## Consequences
- Operational threshold is pinned to explicit confidence level $\alpha$ (default $\alpha=0.05$).
- Calibration metadata is serialized into diagnostics artifacts for full auditability.
