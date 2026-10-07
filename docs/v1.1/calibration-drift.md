# Calibration Drift Monitor

## Overview
The **Calibration Drift Monitor** tracks whether empirical distributions of anomaly scores and escalation rates diverge from the reference calibration baseline established in Phase 4.

## Core Rule: Observational Only (Rule 25)
This monitor NEVER automatically:
- Retrains the model
- Modifies $\alpha$
- Adjusts the conformal threshold
- Overwrites frozen calibration artifacts

When drift is detected, the system transitions to `CALIBRATION REVIEW REQUIRED` and provides an 8-step engineering review checklist.

## Statistical Metrics
- **Population Stability Index (PSI):**
  - $PSI < 0.10$: `STABLE` (no significant change in anomaly score distribution)
  - $0.10 \le PSI < 0.25$: `WATCH` (moderate distribution shift, monitor closely)
  - $PSI \ge 0.25$: `DRIFT DETECTED` (significant distribution shift, action required)
- **Quantile Shifts:** Differences in 25th, 50th (median), 75th, 90th, 95th, and 99th percentiles between reference and current windows.
- **Empirical Escalation Rate Comparison:** Deviation of current escalation rate from nominal reference $\alpha$ (e.g. $4.79\%$ on HDFS).
- **Moments Shift:** Mean and standard deviation delta.

## Suggested Review Workflow
1. Inspect drift metrics and score distribution shifts.
2. Inspect score distribution by log source and tenant.
3. Inspect incident distribution and human adjudication feedback.
4. Inspect false-clear / escalation behavior on recent windows.
5. Run a new calibration experiment in staging environment.
6. Obtain human approval from SRE/Reliability lead.
7. Version new calibration artifact with cryptographic provenance.
8. Evaluate against frozen benchmark before production deployment.
