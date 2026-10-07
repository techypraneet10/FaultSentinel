# ADR-006: Dual-Hash Provenance and Invariant Verification

**Status:** ACCEPTED  
**Date:** 2026-10-07  
**Note:** DOCUMENTED RETROSPECTIVELY  

## Context
When an automated system cites historical logs to justify an incident classification, auditors must be able to verify that the cited log snippet genuinely exists in the historical repository and has not been altered or synthesized.

## Problem
How to guarantee cryptographic immutability and provenance tracking from citation back to the raw source file?

## Options Considered
1. **Raw String Storage:** Store the entire cited log text in the citation payload.
2. **Line Number Indexing:** Rely purely on filename and line numbers (e.g., `train.log:1240`).
3. **Dual-Hash Cryptographic Provenance:** Compute and verify two distinct SHA-256 digests:
   - `source_content_hash`: SHA-256 of canonical exact underlying raw log records.
   - `template_content_hash`: SHA-256 of the normalized Drain3 template token sequence.
   - Bind both to exact file path, commit hash, and line range.

## Decision
Adopt **Dual-Hash Cryptographic Provenance Engine**.

## Reason
- **Tamper Evidence:** Any modification to raw log files or parsed templates breaks hash verification immediately.
- **Normalization Invariance:** Allows verification of structural template matches even across minor variable token perturbations (e.g. varying IP addresses or block IDs).
- **Rule 1 Enforcement:** Formally verifies that retrieved citations stem strictly from the `train` split, preventing test set leakage.

## Trade-offs
- Computation of SHA-256 digests during ingestion and citation bundling.

## Consequences
- Every citation carries verifiable proof of its origin.
- Enables visual inspection in the Evidence Graph and Decision Passport.
