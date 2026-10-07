# Reliability & Fault Injection Lab

## Overview
The **Fault Injection Lab** verifies the resilience and fail-safe boundaries of FaultSentinel when downstream dependencies, network connections, or parsing boundaries experience faults.

## Safety Guard (Rule 16)
Fault injection is strictly environment-gated:
- In `production`: All destructive or simulation scenarios are blocked and return `DISABLED_IN_PRODUCTION`.
- In `local`, `demo`, and `staging`: Controlled, non-destructive fault scenarios execute cleanly against isolated test harnesses.

## Scenarios Matrix
1. **LLM Unavailable / Timeout:**
   - Injected fault: Upstream LLM provider times out.
   - Verified assertion: System falls back gracefully to authoritative Phase 8 deterministic reasoning. Zero fake narratives generated.
2. **Retrieval Unavailable / Empty Evidence:**
   - Injected fault: Retrieval returns zero matching historical chunks.
   - Verified assertion: System emits `INSUFFICIENT_EVIDENCE` with Low severity. Provenance does not falsely pass.
3. **Invalid Log Input:**
   - Injected fault: Log line length > 4096 bytes or malformed schema.
   - Verified assertion: Early rejection with HTTP 422. No stack trace leakage.
4. **Parser Failure:**
   - Injected fault: Corrupted, non-JSON body payload.
   - Verified assertion: Rejected with HTTP 422.
5. **Faithfulness Failure:**
   - Injected fault: Generated narrative missing citation IDs for factual claims.
   - Verified assertion: Faithfulness checker flags `UNSUPPORTED`. UI hides ungrounded text and displays fallback explanation.
6. **Authentication Failure:**
   - Injected fault: Missing or invalid API key / Bearer token.
   - Verified assertion: Rejection with HTTP 401.
7. **Authorization Failure:**
   - Injected fault: Valid token with `analyst` role attempting operator diagnostic routes.
   - Verified assertion: Rejection with HTTP 403.
8. **Configuration Failure:**
   - Injected fault: Malformed YAML/JSON settings.
   - Verified assertion: Configuration validator rejects startup with explicit errors.
9. **Timeout Simulation:**
   - Injected fault: Simulates a long-running pipeline step exceeding threshold.
   - Verified assertion: Returns safe fallback within timeout limits.

## Failure Matrix
Automated test outputs are recorded in `results/v1.1/failure_matrix.json`.
Only statuses `PASS`, `FAIL`, and `NOT_SUPPORTED` are permitted.
