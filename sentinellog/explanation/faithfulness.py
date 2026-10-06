"""Deterministic programmatic faithfulness and grounding checker for Phase 9.

Implements:
1. Claim-to-citation-to-evidence grounding verification (Rule 18).
2. Numeric value faithfulness verification (Rule 19).
3. Citation coverage metric computation (Rule 16).
4. Fixed faithfulness status taxonomy (Rule 38).
5. Contradiction indicator detection for insufficient evidence and conflict states.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinellog.explanation.schemas import (
    ClaimType,
    ExplanationClaim,
    FaithfulnessResult,
    FaithfulnessStatus,
)
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.schemas import IncidentAssessment

# Words ignored during lexical overlap checking
STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "is",
    "are", "was", "were", "this", "that", "it", "with", "as", "by", "from",
    "be", "has", "have", "had", "not", "but", "observed", "evidence", "log",
    "window", "system", "event", "events", "chunk", "chunks",
}


def extract_content_tokens(text: str) -> Set[str]:
    """Tokenize text into lowercase alphanumeric content words, removing stopwords."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def extract_numbers(text: str) -> List[float]:
    """Extract floating point and integer numbers from text."""
    raw_nums = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    nums = []
    for rn in raw_nums:
        try:
            val = float(rn)
            nums.append(val)
        except ValueError:
            pass
    return nums


class FaithfulnessChecker:
    """Programmatic, deterministic grounding and faithfulness verification engine."""

    def __init__(
        self,
        min_lexical_overlap: float = 0.05,
        coverage_threshold: float = 0.70,
    ):
        self.min_lexical_overlap = min_lexical_overlap
        self.coverage_threshold = coverage_threshold

    def _collect_trusted_numbers(
        self,
        assessment: IncidentAssessment,
        bundle: Optional[CitationBundle],
    ) -> Set[float]:
        """Collect all known legitimate numbers from Phase 8 assessment and Phase 7 citations."""
        trusted: Set[float] = {float(i) for i in range(11)} | {100.0}
        trusted.add(round(assessment.confidence, 2))
        trusted.add(round(assessment.confidence, 4))

        # Signals
        for s_name, s_data in assessment.reasoning_trace.signals.items():
            val = s_data.get("value")
            if isinstance(val, (int, float)):
                trusted.add(round(float(val), 2))
                trusted.add(round(float(val), 4))
            elif isinstance(val, dict):
                for sub_k, sub_v in val.items():
                    if isinstance(sub_v, (int, float)):
                        trusted.add(round(float(sub_v), 2))
                        trusted.add(round(float(sub_v), 4))

        # Citations
        if bundle:
            for cit in bundle.citations:
                trusted.add(float(cit.selected_rank))
                trusted.add(round(cit.retrieval_score, 2))
                trusted.add(round(cit.retrieval_score, 4))
                trusted.add(round(cit.selection_score, 2))
                trusted.add(round(cit.selection_score, 4))
                if cit.provenance and cit.provenance.source_location:
                    loc = cit.provenance.source_location
                    if loc.line_start is not None:
                        trusted.add(float(loc.line_start))
                    if loc.line_end is not None:
                        trusted.add(float(loc.line_end))
                    trusted.add(float(loc.record_count))

        return trusted

    def evaluate(
        self,
        claims: List[ExplanationClaim],
        assessment: IncidentAssessment,
        bundle: Optional[CitationBundle],
        raw_excerpts: Optional[Dict[str, str]] = None,
    ) -> Tuple[FaithfulnessResult, float]:
        """Perform programmatic grounding verification across claims.
        
        Args:
            claims: Parsed ExplanationClaim instances.
            assessment: Authoritative Phase 8 assessment.
            bundle: Authoritative Phase 7 CitationBundle.
            raw_excerpts: Dictionary of citation ID to text excerpts.
            
        Returns:
            Tuple of:
                - FaithfulnessResult object
                - citation_coverage float [0.0, 1.0]
        """
        raw_excerpts = raw_excerpts or {}
        valid_bundle_cids = set(c.citation_id for c in bundle.citations) if bundle else set()
        trusted_numbers = self._collect_trusted_numbers(assessment, bundle)

        bundle_text_tokens: Dict[str, Set[str]] = {}
        if bundle:
            for cit in bundle.citations:
                text_corpus = raw_excerpts.get(cit.citation_id, "") + " " + cit.citation_text
                bundle_text_tokens[cit.citation_id] = extract_content_tokens(text_corpus)

        factual_claims = [c for c in claims if c.is_factual]
        total_factual = len(factual_claims)
        supported_factual = 0
        unsupported_claims: List[str] = []
        contradictions: List[str] = []
        numeric_failed = False

        for claim in claims:
            claim_text = claim.text
            claim_tokens = extract_content_tokens(claim_text)

            # Check 1: Numeric Consistency
            # If claim cites numbers, verify against trusted set
            claim_nums = extract_numbers(claim_text)
            for c_num in claim_nums:
                rounded_c_num_2 = round(c_num, 2)
                rounded_c_num_4 = round(c_num, 4)
                if rounded_c_num_2 not in trusted_numbers and rounded_c_num_4 not in trusted_numbers:
                    # Flag numeric mismatch
                    numeric_failed = True
                    claim.validation_notes.append(f"Unverified numeric value: {c_num}")

            # Check 2: Contradiction Check for INSUFFICIENT_EVIDENCE
            if assessment.decision == "INSUFFICIENT_EVIDENCE":
                if re.search(r"\b(confirmed incident|definite attack|verified failure|incident confirmed)\b", claim_text, re.IGNORECASE):
                    contradictions.append(
                        f"Claim asserts confirmed incident despite INSUFFICIENT_EVIDENCE: '{claim_text}'"
                    )

            # Check 3: Factual Grounding Verification
            if claim.is_factual:
                if not claim.citation_ids:
                    claim.supported = False
                    claim.support_score = 0.0
                    claim.validation_notes.append("Factual claim lacks required citations.")
                    unsupported_claims.append(claim.text)
                    continue

                # Verify all cited IDs belong to the bundle
                valid_cids = [cid for cid in claim.citation_ids if cid in valid_bundle_cids]
                if not valid_cids:
                    claim.supported = False
                    claim.support_score = 0.0
                    claim.validation_notes.append("All cited citation IDs are invalid or not in bundle.")
                    unsupported_claims.append(claim.text)
                    continue

                # Verify lexical overlap with evidence text
                cited_evidence_tokens = set()
                for cid in valid_cids:
                    cited_evidence_tokens.update(bundle_text_tokens.get(cid, set()))

                if not claim_tokens:
                    overlap_ratio = 1.0
                else:
                    common_tokens = claim_tokens.intersection(cited_evidence_tokens)
                    overlap_ratio = len(common_tokens) / len(claim_tokens)

                claim.support_score = round(overlap_ratio, 4)

                # A factual claim is supported if cited valid IDs and has non-zero overlap or valid signals
                if overlap_ratio >= self.min_lexical_overlap or any(
                    sig_word in claim_tokens for sig_word in {"anomaly", "score", "escalation", "repeated", "window", "connection"}
                ):
                    claim.supported = True
                    supported_factual += 1
                else:
                    claim.supported = False
                    claim.validation_notes.append(f"Insufficient lexical overlap ({overlap_ratio:.2f}) with cited evidence.")
                    unsupported_claims.append(claim.text)
            else:
                # Non-factual claims (INTERPRETATION, UNCERTAINTY, RECOMMENDATION)
                claim.supported = True
                claim.support_score = 1.0

        # Calculate coverage
        citation_coverage = round(float(supported_factual / total_factual), 4) if total_factual > 0 else 1.0

        # Determine FaithfulnessStatus
        if contradictions:
            status = FaithfulnessStatus.INVALID.value
        elif total_factual == 0:
            status = FaithfulnessStatus.VERIFIED.value
        elif citation_coverage >= self.coverage_threshold and not numeric_failed:
            status = FaithfulnessStatus.VERIFIED.value
        elif citation_coverage > 0.0:
            status = FaithfulnessStatus.PARTIALLY_SUPPORTED.value
        else:
            status = FaithfulnessStatus.UNSUPPORTED.value

        grounding_score = round((citation_coverage + (0.0 if numeric_failed else 1.0)) / 2.0, 4)

        result = FaithfulnessResult(
            status=status,
            grounding_score=grounding_score,
            claims_checked=len(claims),
            claims_supported=supported_factual + (len(claims) - total_factual),
            numeric_checks_passed=not numeric_failed,
            unsupported_claims=unsupported_claims,
            contradictions_detected=contradictions,
            details={
                "total_factual_claims": total_factual,
                "supported_factual_claims": supported_factual,
                "citation_coverage": citation_coverage,
            },
        )
        return result, citation_coverage
