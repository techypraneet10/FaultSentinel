"""Claim extraction, categorization, and claim-level taxonomy enforcement.

Enforces:
1. Fixed vocabulary taxonomy (Rule 14):
   OBSERVATION, EVIDENCE, CORRELATION, INTERPRETATION, UNCERTAINTY, RECOMMENDATION.
2. Factual vs. non-factual claim boundary (Rule 12).
3. Root cause caution language constraints (Rule 24).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinellog.explanation.exceptions import ClaimValidationError
from sentinellog.explanation.schemas import ClaimType, ExplanationClaim

# Causal trigger phrases requiring explicit evidence backing
UNSUPPORTED_CAUSAL_PATTERNS = [
    r"\bcaused by\b",
    r"\bcrashed because\b",
    r"\bunderlying root cause is\b",
    r"\bdefinitively caused\b",
    r"\bfailure is due to\b",
]


class ClaimExtractor:
    """Parses and validates individual claims from structured LLM outputs."""

    def __init__(self, allowed_types: Optional[Set[str]] = None):
        self.allowed_types = allowed_types or {t.value for t in ClaimType}

    def parse_claims(
        self,
        raw_claims: List[Dict[str, Any]],
        window_id: str = "win",
    ) -> List[ExplanationClaim]:
        """Convert raw claim dictionaries to typed ExplanationClaim instances.
        
        Args:
            raw_claims: List of dictionaries from LLM JSON response.
            window_id: Query window identifier for claim ID derivation.
            
        Returns:
            List of parsed ExplanationClaim objects.
        """
        parsed: List[ExplanationClaim] = []

        for idx, item in enumerate(raw_claims, 1):
            text = str(item.get("text", "")).strip()
            if not text:
                continue

            raw_type = str(item.get("claim_type", "OBSERVATION")).strip().upper()
            if raw_type not in self.allowed_types:
                # Default unknown types to INTERPRETATION to prevent ungrounded factual leakage
                claim_type = ClaimType.INTERPRETATION.value
            else:
                claim_type = raw_type

            raw_cit_ids = item.get("citation_ids", [])
            if isinstance(raw_cit_ids, list):
                citation_ids = [str(cid).strip() for cid in raw_cit_ids if str(cid).strip()]
            elif isinstance(raw_cit_ids, str) and raw_cit_ids.strip():
                citation_ids = [raw_cit_ids.strip()]
            else:
                citation_ids = []

            is_factual = ClaimType.is_factual(claim_type)
            claim_id = f"CLM-{window_id[:16]}-{idx:03d}"

            # Check for strong causal claims
            notes = []
            for pattern in UNSUPPORTED_CAUSAL_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    notes.append(f"Causal assertion detected: '{pattern}'")

            parsed.append(
                ExplanationClaim(
                    claim_id=claim_id,
                    text=text,
                    claim_type=claim_type,
                    citation_ids=citation_ids,
                    is_factual=is_factual,
                    supported=False,  # Evaluated downstream by FaithfulnessChecker
                    support_score=0.0,
                    validation_notes=notes,
                )
            )

        return parsed
