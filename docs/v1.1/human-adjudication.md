# Human Adjudication & Audit Review

## Overview
FaultSentinel v1.1 includes a lightweight human review interface enabling on-call SREs to record adjudication outcomes on automated triage decisions.

## Adjudication Decisions
- `CONFIRM`: The human reviewer agrees with the machine decision and root cause.
- `REJECT`: The human reviewer disagrees with the machine decision. A mandatory failure reason must be supplied:
  - `False Positive`
  - `Insufficient Evidence`
  - `Wrong Severity`
  - `Wrong Root Cause`
  - `Missing Evidence`
  - `Other`
- `NEEDS_REVIEW`: Ambiguous incident flagged for senior engineering review.

## Rule 9: Non-Invasive Audit Signal
Human feedback is strictly an operational review and audit telemetry signal:
- It **NEVER** automatically retrains models.
- It **NEVER** mutates conformal calibration parameters.
- It **NEVER** modifies frozen benchmark results.
- Stored review records are saved to `results/v1.1/human_reviews.json` for periodic compliance auditing.
