"""Audit and integrity verification engine for Phase 7 evidence citations.

Verifies:
1. Structural integrity: Validates field schemas, non-empty fields, and TRAIN split invariants.
2. Source addressability: Resolves citation back to physical Phase 2 artifacts.
3. Content integrity: Compares stored content_hash against freshly recomputed hash.
4. Anomaly label isolation: Verifies that labels are absent from citation text and IDs.
"""

from typing import Any, Dict, List, Optional

from sentinellog.provenance.hashing import compute_citation_id, compute_content_hash
from sentinellog.provenance.resolver import ProvenanceResolutionError, SourceResolver
from sentinellog.provenance.schemas import (
    Citation,
    CitationBundle,
    EvidenceProvenance,
    VerificationResult,
)
from sentinellog.retrieval.guards import guard_no_label_in_text, guard_train_split_only


class CitationValidationError(Exception):
    """Raised when a citation violates structural invariants or research integrity rules."""
    pass


class ProvenanceVerifier:
    """Verifies citation provenance records and validates end-to-end source integrity."""

    def __init__(self, resolver: Optional[SourceResolver] = None):
        """Initialize verifier.

        Args:
            resolver: Optional SourceResolver instance. If None, a default instance is created.
        """
        self.resolver = resolver or SourceResolver()

    def verify_citation(self, citation: Citation) -> VerificationResult:
        """Verify round-trip integrity and addressability of a single citation.

        Args:
            citation: Citation object to verify.

        Returns:
            VerificationResult detailing validation status and hash check.
        """
        cid = citation.citation_id
        prov = citation.provenance

        # 1. Structural and Leakage Guards
        try:
            guard_train_split_only(citation.split)
            guard_train_split_only(prov.split)
            guard_no_label_in_text(citation.citation_text)
        except Exception as e:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=False,
                source_content_hash_match=False,
                template_content_hash_match=False,
                stored_source_hash=citation.source_content_hash,
                stored_template_hash=citation.template_content_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=None,
                message=f"Guard violation: {str(e)}",
            )

        # 2. Recompute and verify citation ID determinism
        expected_cid = compute_citation_id(
            dataset=citation.dataset,
            split=citation.split,
            chunk_id=citation.chunk_id,
            source_window_id=citation.source_window_id,
            line_start=prov.source_location.line_start,
            line_end=prov.source_location.line_end,
        )
        if cid != expected_cid:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=False,
                source_content_hash_match=False,
                template_content_hash_match=False,
                stored_source_hash=citation.source_content_hash,
                stored_template_hash=citation.template_content_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=None,
                message=f"Citation ID mismatch: expected '{expected_cid}', got '{cid}'.",
            )

        # 3. Resolve source from physical artifact
        try:
            artifact, location, canon_text, recomputed_source_hash, recomputed_template_hash = (
                self.resolver.resolve_source(
                    dataset=citation.dataset,
                    split=citation.split,
                    source_window_id=citation.source_window_id,
                )
            )
        except ProvenanceResolutionError as e:
            return VerificationResult(
                citation_id=cid,
                status="UNRESOLVED",
                content_hash_match=False,
                source_content_hash_match=False,
                template_content_hash_match=False,
                stored_source_hash=citation.source_content_hash,
                stored_template_hash=citation.template_content_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=None,
                message=f"Source could not be resolved: {str(e)}",
            )
        except Exception as e:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=False,
                source_content_hash_match=False,
                template_content_hash_match=False,
                stored_source_hash=citation.source_content_hash,
                stored_template_hash=citation.template_content_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=None,
                message=f"Unexpected error resolving source: {str(e)}",
            )

        # 4. Check Content Hash Integrity (Separate exact source-record and template hashes)
        source_hash_match = (citation.source_content_hash == recomputed_source_hash)
        template_hash_match = (citation.template_content_hash == recomputed_template_hash)

        if not source_hash_match:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=False,
                source_content_hash_match=False,
                template_content_hash_match=template_hash_match,
                stored_source_hash=citation.source_content_hash,
                recomputed_source_hash=recomputed_source_hash,
                stored_template_hash=citation.template_content_hash,
                recomputed_template_hash=recomputed_template_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=recomputed_source_hash,
                message="Integrity check failed: stored source_content_hash does not match recomputed hash from underlying source records.",
            )

        if not template_hash_match:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=False,
                source_content_hash_match=True,
                template_content_hash_match=False,
                stored_source_hash=citation.source_content_hash,
                recomputed_source_hash=recomputed_source_hash,
                stored_template_hash=citation.template_content_hash,
                recomputed_template_hash=recomputed_template_hash,
                stored_hash=citation.template_content_hash,
                recomputed_hash=recomputed_template_hash,
                message="Integrity check failed: stored template_content_hash does not match recomputed hash from template tokens.",
            )

        # 5. Check Artifact Hash Consistency
        if prov.source_artifact.artifact_sha256 != artifact.artifact_sha256:
            return VerificationResult(
                citation_id=cid,
                status="INVALID",
                content_hash_match=True,
                source_content_hash_match=True,
                template_content_hash_match=True,
                stored_source_hash=citation.source_content_hash,
                recomputed_source_hash=recomputed_source_hash,
                stored_template_hash=citation.template_content_hash,
                recomputed_template_hash=recomputed_template_hash,
                stored_hash=citation.source_content_hash,
                recomputed_hash=recomputed_source_hash,
                message="Source artifact hash mismatch: physical file has been modified.",
            )

        return VerificationResult(
            citation_id=cid,
            status="VALID",
            content_hash_match=True,
            source_content_hash_match=True,
            template_content_hash_match=True,
            stored_source_hash=citation.source_content_hash,
            recomputed_source_hash=recomputed_source_hash,
            stored_template_hash=citation.template_content_hash,
            recomputed_template_hash=recomputed_template_hash,
            stored_hash=citation.source_content_hash,
            recomputed_hash=recomputed_source_hash,
            message="Citation successfully resolved and dual-hash integrity verified.",
        )


    def verify_bundle(self, bundle: CitationBundle) -> Dict[str, Any]:
        """Verify all citations within a bundle and evaluate overall integrity.

        Args:
            bundle: CitationBundle to verify.

        Returns:
            Dictionary summarizing verification counts, statuses, and individual results.
        """
        results: List[VerificationResult] = [self.verify_citation(c) for c in bundle.citations]
        valid_count = sum(1 for r in results if r.status == "VALID")
        invalid_count = sum(1 for r in results if r.status == "INVALID")
        unresolved_count = sum(1 for r in results if r.status == "UNRESOLVED")

        all_ok = (valid_count == len(results)) and (len(results) > 0 or bundle.evidence_count == 0)
        bundle.all_verified = all_ok

        return {
            "bundle_id": bundle.bundle_id,
            "query_id": bundle.query_id,
            "total_citations": len(results),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "unresolved_count": unresolved_count,
            "all_verified": all_ok,
            "results": [r.to_dict() for r in results],
        }
