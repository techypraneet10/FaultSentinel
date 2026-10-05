"""Provenance and citation engine for Phase 7 of SentinelLog.

Consumes Phase 6 selected evidence sets, generates cryptographic, human-readable citations,
derives deterministic citation bundles, and coordinates round-trip source resolution and verification.
"""

from typing import List, Optional, Sequence

from sentinellog.provenance.hashing import (
    compute_bundle_id,
    compute_citation_id,
    compute_content_hash,
    format_citation_text,
)
from sentinellog.provenance.resolver import SourceResolver
from sentinellog.provenance.schemas import (
    Citation,
    CitationBundle,
    EvidenceProvenance,
    SourceArtifact,
    SourceLocation,
)
from sentinellog.provenance.verifier import ProvenanceVerifier
from sentinellog.retrieval.guards import guard_train_split_only
from sentinellog.retrieval.reranking_schemas import SelectedEvidence
from sentinellog.scoring.artifacts import get_git_commit_sha


class ProvenanceEngine:
    """Coordinates generation of verifiable citations and citation bundles for selected evidence."""

    def __init__(
        self,
        resolver: Optional[SourceResolver] = None,
        verifier: Optional[ProvenanceVerifier] = None,
        provenance_version: str = "1.0",
        source_commit: Optional[str] = None,
    ):
        """Initialize engine.

        Args:
            resolver: Optional SourceResolver instance.
            verifier: Optional ProvenanceVerifier instance.
            provenance_version: Provenance schema version string.
            source_commit: Optional git commit SHA.
        """
        self.resolver = resolver or SourceResolver()
        self.verifier = verifier or ProvenanceVerifier(resolver=self.resolver)
        self.provenance_version = provenance_version
        self.source_commit = source_commit or get_git_commit_sha()

    def create_citation(
        self,
        evidence: SelectedEvidence,
    ) -> Citation:
        """Create a verifiable, deterministic citation from a single selected evidence item.

        Args:
            evidence: SelectedEvidence instance from Phase 6.

        Returns:
            Citation instance with full provenance and content hash.
        """
        guard_train_split_only(evidence.split)

        # 1. Resolve exact physical source coordinates
        artifact, location, canon_text, source_content_hash, template_content_hash = (
            self.resolver.resolve_source(
                dataset=evidence.dataset,
                split=evidence.split,
                source_window_id=evidence.source_window_id,
            )
        )

        # 2. Derive deterministic citation ID
        citation_id = compute_citation_id(
            dataset=evidence.dataset,
            split=evidence.split,
            chunk_id=evidence.chunk_id,
            source_window_id=evidence.source_window_id,
            line_start=location.line_start,
            line_end=location.line_end,
        )

        # 3. Format canonical human-readable citation text
        citation_text = format_citation_text(
            dataset=evidence.dataset,
            split=evidence.split,
            source_window_id=evidence.source_window_id,
            location=location,
        )

        # 4. Construct complete EvidenceProvenance record
        provenance = EvidenceProvenance(
            citation_id=citation_id,
            chunk_id=evidence.chunk_id,
            dataset=evidence.dataset,
            split=evidence.split,
            source_window_id=evidence.source_window_id,
            source_artifact=artifact,
            source_location=location,
            source_content_hash=source_content_hash,
            template_content_hash=template_content_hash,
            content_hash=source_content_hash,
            provenance_version=self.provenance_version,
            source_commit=self.source_commit,
        )

        # 5. Return immutable Citation object
        return Citation(
            citation_id=citation_id,
            citation_text=citation_text,
            chunk_id=evidence.chunk_id,
            source_window_id=evidence.source_window_id,
            dataset=evidence.dataset,
            split=evidence.split,
            selected_rank=evidence.selected_rank,
            retrieval_score=evidence.retrieval_score,
            selection_score=evidence.selection_score,
            source_content_hash=source_content_hash,
            template_content_hash=template_content_hash,
            content_hash=source_content_hash,
            provenance=provenance,
        )


    def create_bundle(
        self,
        query_id: str,
        dataset: str,
        selected_evidence: Sequence[SelectedEvidence],
        verify: bool = True,
    ) -> CitationBundle:
        """Create a deterministic CitationBundle for an escalated query's selected evidence.

        Args:
            query_id: Identifier of escalated query window.
            dataset: Target dataset name.
            selected_evidence: Ordered sequence of SelectedEvidence items matching Phase 6 rank.
            verify: If True, executes round-trip verification across all citations.

        Returns:
            CitationBundle instance containing all ordered citations.
        """
        citations: List[Citation] = [self.create_citation(e) for e in selected_evidence]
        citation_ids = [c.citation_id for c in citations]

        bundle_id = compute_bundle_id(
            citation_ids=citation_ids,
            dataset=dataset,
            provenance_version=self.provenance_version,
        )

        bundle = CitationBundle(
            bundle_id=bundle_id,
            query_id=query_id,
            dataset=dataset,
            split="train",
            evidence_count=len(citations),
            citations=citations,
            provenance_version=self.provenance_version,
            source_commit=self.source_commit,
            all_verified=False,
        )

        if verify and len(citations) > 0:
            v_res = self.verifier.verify_bundle(bundle)
            bundle.all_verified = v_res["all_verified"]
        elif len(citations) == 0:
            bundle.all_verified = True

        return bundle
