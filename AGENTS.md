# SentinelLog Research Integrity Guardrails & Agent Instructions

This document defines the permanent, non-negotiable operational rules for all AI agents and human contributors working on the SentinelLog codebase.

---

## RULE 1 — TEST SET PROTECTION
NEVER read, print, load, inspect, process, train on, tune against, or compute metrics on `data/test/` until Phase 7.
The test set is frozen until the frozen-evaluation phase.
No exceptions unless explicitly authorized in the Phase 7 evaluation workflow.

---

## RULE 2 — CHRONOLOGICAL SPLITS
All dataset splits must be chronological.
Never randomly shuffle temporal log data when constructing train/calibration/test splits. Log sequences have strict temporal dependencies; random shuffling introduces severe data leakage.

---

## RULE 3 — EXPERIMENT TRACEABILITY
Every experiment run must record:
- Random seed
- Model and hyperparameters
- Dataset name and data version
- Configuration details
- Relevant code version / git commit hash

No reported experimental number may exist without traceable configuration and code provenance.

---

## RULE 4 — LLM API ISOLATION
No network calls to an LLM API except from the explanation component in the appropriate later phase and only for approved log windows.
Phase 1 must make ZERO LLM API calls. Future phases must isolate and sandbox LLM API interactions strictly within the approved escalation budget.

---

## RULE 5 — DEPENDENCY DISCIPLINE
Do not add dependencies outside `requirements.txt` without explicit approval.
Prefer the smallest dependency set that satisfies the project requirements. Keep environments reproducible and lightweight.

---

## RULE 6 — MODEL SIZE
Keep learned scorer models small.
The scorer parameter count must remain under 2 million parameters.
This constraint applies to the later B2 scorer.

---

## RULE 7 — NO FABRICATED RESULTS
Never invent, estimate, simulate, or fabricate experimental results.
If an experiment has not been executed, mark it as `NOT RUN / TBD`. All benchmark metrics must stem directly from verified, recorded execution outputs.

---

## RULE 8 — HUMAN CHECKPOINTS
Antigravity must not treat its own completion statement as sufficient evidence.
Every phase has a human verification checkpoint.
The agent must report what the human should verify before the next phase begins.

---

## RULE 9 — SMALL, VERIFIABLE WORK UNITS
Each agent session should implement one narrowly defined unit of work and verify it with tests or deterministic checks. Avoid sprawling, untestable batches of modifications.

---

## RULE 10 — DO NOT DRIFT INTO FUTURE PHASES
Only implement the current authorized phase.
Do not proactively implement later architecture, models, deployment, evaluation, or optimization. Premature logic violates phase gates and invites unverified complexity.
