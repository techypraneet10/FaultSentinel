"""Citation extraction, verification, and precision calculation for Phase 9.

Enforces:
1. Exact citation matching against Phase 7 bundles (Rule 11).
2. Provenance verification gate (Rule 15).
3. Citation precision metric computation (Rule 17).
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from sentinellog.explanation.exceptions import CitationValidationError
from sentinellog.explanation.schemas import CitationValidationStatus, ExplanationCitation
from sentinellog.provenance.schemas import Citation, CitationBundle


class CitationValidator:
    """Validates cited references against the authoritative Phase 7 citation bundle."""

    def __init__(self, strict_provenance: bool = True):
        self.strict_provenance = strict_provenance

    def validate_citations(
        self,
        cited_ids: List[str],
        bundle: Optional[CitationBundle],
    ) -> Tuple[CitationValidationStatus, float, List[ExplanationCitation], List[str]]:
        """Validate list of citation IDs against the authoritative bundle.
        
        Args:
            cited_ids: Citation IDs cited by claims or summary.
            bundle: The authoritative Phase 7 CitationBundle for this window.
            
        Returns:
            Tuple of:
                - CitationValidationStatus ('VALID' or 'INVALID')
                - citation_precision (float [0.0, 1.0])
                - List of resolved ExplanationCitation objects
                - List of validation error messages
        """
        if not bundle:
            if not cited_ids:
                return CitationValidationStatus.VALID, 1.0, [], []
            return (
                CitationValidationStatus.INVALID,
                0.0,
                [],
                [f"Citations referenced ({cited_ids}) but no CitationBundle was provided."],
            )

        bundle_citation_map: Dict[str, Citation] = {c.citation_id: c for c in bundle.citations}
        errors: List[str] = []
        resolved_citations: List[ExplanationCitation] = []
        valid_refs = 0
        total_refs = len(cited_ids)

        seen_cited: Set[str] = set()
        for cid in cited_ids:
            clean_cid = str(cid).strip()
            if not clean_cid:
                continue

            if clean_cid not in bundle_citation_map:
                errors.append(f"Cited ID '{clean_cid}' does not exist in authoritative Phase 7 bundle.")
                continue

            cit = bundle_citation_map[clean_cid]

            # Check provenance status
            prov_status = cit.provenance.source_artifact.dataset if cit.provenance else "UNKNOWN"
            # Phase 7 all_verified check
            if self.strict_provenance and not bundle.all_verified:
                errors.append(f"Citation '{clean_cid}' belongs to unverified bundle '{bundle.bundle_id}'.")
                continue

            valid_refs += 1

            if clean_cid not in seen_cited:
                seen_cited.add(clean_cid)
                loc_dict = cit.provenance.source_location.to_dict() if cit.provenance else {}
                resolved_citations.append(
                    ExplanationCitation(
                        citation_id=cit.citation_id,
                        citation_text=cit.citation_text,
                        chunk_id=cit.chunk_id,
                        source_window_id=cit.source_window_id,
                        dataset=cit.dataset,
                        split=cit.split,
                        selected_rank=cit.selected_rank,
                        retrieval_score=cit.retrieval_score,
                        selection_score=cit.selection_score,
                        provenance_status="VERIFIED" if bundle.all_verified else "UNVERIFIED",
                        source_location=loc_dict,
                    )
                )

        if total_refs == 0:
            precision = 1.0
        else:
            precision = round(float(valid_refs / total_refs), 4)

        status = CitationValidationStatus.VALID if not errors else CitationValidationStatus.INVALID
        return status, precision, resolved_citations, errors
