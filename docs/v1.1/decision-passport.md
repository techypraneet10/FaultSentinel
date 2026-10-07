# Decision Passport & Cryptographic Auditing

## Overview
The **Decision Passport** is a compact, machine-verifiable audit artifact generated for completed incident decisions. It binds the final decision to its exact statistical parameters, retrieved evidence, and code revision.

## Cryptographic Structure
The passport calculates three distinct SHA-256 digests:
1. `configuration_hash`: SHA-256 of $(\alpha, \tau_\alpha, \text{dataset}, \text{version})$.
2. `evidence_hash`: SHA-256 of the retrieved chunks, MMR selections, and citation count.
3. `decision_hash`: A root digest binding:
   $$\text{SHA-256}(\text{IncidentID} \mid \text{Dataset} \mid \text{WindowID} \mid \text{Score} \mid \text{Threshold} \mid \text{ConformalDecision} \mid \text{FinalDecision} \mid \text{Severity} \mid \text{ConfigHash} \mid \text{EvidenceHash} \mid \text{GitCommit})$$

## Verification
Any party with access to the decision passport can call `/api/v1/incidents/{incident_id}/passport/verify` to cryptographically prove that:
- The decision was not modified post-generation.
- The conformal parameters match the recorded state.
- The software version and git commit match the release provenance.
