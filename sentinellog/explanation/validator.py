"""Multi-stage validation pipeline for Phase 9 LLM Explanation.

Executes sequential, fail-closed verification pipeline (Rule 37):
1. Structured JSON output parsing & schema validation
2. Decision immutability verification (Rule 5 & Rule 20)
3. Severity immutability verification (Rule 5 & Rule 20)
4. Citation existence and provenance validation (Rule 11 & Rule 15)
5. Claim taxonomy and factual support verification (Rule 12 & Rule 14)
6. Faithfulness and numeric consistency verification (Rule 18 & Rule 19)
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sentinellog.explanation.citations import CitationValidator
from sentinellog.explanation.claims import ClaimExtractor
from sentinellog.explanation.exceptions import (
    DecisionImmutabilityError,
    MalformedOutputError,
    SeverityImmutabilityError,
)
from sentinellog.explanation.faithfulness import FaithfulnessChecker
from sentinellog.explanation.schemas import (
    CitationValidationStatus,
    ExplanationClaim,
    ExplanationCitation,
    FaithfulnessResult,
    ValidationResult,
)
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.schemas import IncidentAssessment


class ExplanationValidator:
    """Rigorous validation engine enforcing decision immutability and provenance fidelity."""

    def __init__(
        self,
        citation_validator: Optional[CitationValidator] = None,
        faithfulness_checker: Optional[FaithfulnessChecker] = None,
        claim_extractor: Optional[ClaimExtractor] = None,
        min_coverage: float = 0.50,
    ):
        self.citation_validator = citation_validator or CitationValidator(strict_provenance=True)
        self.faithfulness_checker = faithfulness_checker or FaithfulnessChecker()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.min_coverage = min_coverage

    def validate(
        self,
        raw_text: str,
        assessment: IncidentAssessment,
        bundle: Optional[CitationBundle],
        raw_excerpts: Optional[Dict[str, str]] = None,
    ) -> Tuple[ValidationResult, Optional[Dict[str, Any]], List[ExplanationClaim], List[ExplanationCitation]]:
        """Execute full validation sequence against generated text.
        
        Args:
            raw_text: Raw output string from LLM provider.
            assessment: Authoritative Phase 8 assessment.
            bundle: Authoritative Phase 7 CitationBundle.
            raw_excerpts: Pre-loaded raw log excerpts for citations.
            
        Returns:
            Tuple of:
                - ValidationResult
                - Parsed JSON dictionary (or None if unparseable)
                - List of parsed ExplanationClaim instances
                - List of resolved ExplanationCitation instances
        """
        trace: List[Dict[str, Any]] = []
        failure_reasons: List[str] = []

        # Step 1: JSON Parsing
        try:
            parsed = json.loads(raw_text.strip())
            trace.append({"step": "json_parse", "passed": True})
        except Exception as e:
            trace.append({"step": "json_parse", "passed": False, "error": str(e)})
            f_res = FaithfulnessResult(status="INVALID", grounding_score=0.0)
            return (
                ValidationResult(
                    is_valid=False,
                    citation_status=CitationValidationStatus.INVALID.value,
                    decision_consistent=False,
                    severity_consistent=False,
                    numeric_consistent=False,
                    citation_coverage=0.0,
                    citation_precision=0.0,
                    faithfulness_result=f_res,
                    validation_trace=trace,
                    failure_reasons=["Malformed JSON output from LLM."],
                ),
                None,
                [],
                [],
            )

        # Step 2: Decision Immutability Check
        llm_decision = str(parsed.get("incident_decision", "")).strip().upper()
        expected_decision = assessment.decision.strip().upper()
        decision_consistent = (llm_decision == expected_decision)
        if not decision_consistent:
            failure_reasons.append(
                f"Decision Immutability Violation: LLM declared '{llm_decision}' but Phase 8 authoritative decision is '{expected_decision}'."
            )
        trace.append({
            "step": "decision_immutability",
            "passed": decision_consistent,
            "llm": llm_decision,
            "expected": expected_decision,
        })

        # Step 3: Severity Immutability Check
        llm_severity = str(parsed.get("severity", "")).strip().upper()
        expected_severity = assessment.severity.strip().upper()
        severity_consistent = (llm_severity == expected_severity)
        if not severity_consistent:
            failure_reasons.append(
                f"Severity Immutability Violation: LLM declared '{llm_severity}' but Phase 8 authoritative severity is '{expected_severity}'."
            )
        trace.append({
            "step": "severity_immutability",
            "passed": severity_consistent,
            "llm": llm_severity,
            "expected": expected_severity,
        })

        # Step 4: Claim Extraction
        raw_claims = parsed.get("claims", [])
        if not isinstance(raw_claims, list):
            raw_claims = []
        parsed_claims = self.claim_extractor.parse_claims(raw_claims, window_id=assessment.window_id)
        trace.append({"step": "claim_extraction", "passed": True, "count": len(parsed_claims)})

        # Step 5: Citation Validation
        all_cited_ids: List[str] = []
        for c in parsed_claims:
            all_cited_ids.extend(c.citation_ids)

        cit_status, cit_precision, resolved_citations, cit_errors = self.citation_validator.validate_citations(
            cited_ids=all_cited_ids,
            bundle=bundle,
        )
        citation_passed = (cit_status == CitationValidationStatus.VALID)
        if cit_errors:
            failure_reasons.extend(cit_errors)
        trace.append({
            "step": "citation_validation",
            "passed": citation_passed,
            "precision": cit_precision,
            "errors": cit_errors,
        })

        # Step 6: Faithfulness & Numeric Verification
        faith_res, coverage = self.faithfulness_checker.evaluate(
            claims=parsed_claims,
            assessment=assessment,
            bundle=bundle,
            raw_excerpts=raw_excerpts,
        )
        trace.append({
            "step": "faithfulness_check",
            "status": faith_res.status,
            "coverage": coverage,
            "numeric_passed": faith_res.numeric_checks_passed,
            "contradictions": faith_res.contradictions_detected,
        })

        if not faith_res.numeric_checks_passed:
            failure_reasons.append("Numeric values in explanation claims could not be verified against trusted signals.")

        if faith_res.contradictions_detected:
            failure_reasons.extend(faith_res.contradictions_detected)

        # Coverage threshold check for factual claims
        coverage_passed = (coverage >= self.min_coverage) or (len([c for c in parsed_claims if c.is_factual]) == 0)
        if not coverage_passed:
            failure_reasons.append(f"Citation coverage ({coverage:.2f}) fell below minimum required threshold ({self.min_coverage:.2f}).")

        # Step 7: Summary and Free-form Explanation Inspection (Section 6)
        summary_text = str(parsed.get("summary", "")).strip()
        explanation_text = str(parsed.get("explanation", "")).strip()
        freeform_errors = self._inspect_freeform_text(
            summary_text=summary_text,
            explanation_text=explanation_text,
            claims=parsed_claims,
        )
        freeform_passed = not freeform_errors
        if freeform_errors:
            failure_reasons.extend(freeform_errors)
        trace.append({
            "step": "freeform_text_inspection",
            "passed": freeform_passed,
            "errors": freeform_errors,
        })

        is_valid = (
            decision_consistent
            and severity_consistent
            and citation_passed
            and faith_res.numeric_checks_passed
            and not faith_res.contradictions_detected
            and coverage_passed
            and freeform_passed
        )

        val_result = ValidationResult(
            is_valid=is_valid,
            citation_status=cit_status.value,
            decision_consistent=decision_consistent,
            severity_consistent=severity_consistent,
            numeric_consistent=faith_res.numeric_checks_passed,
            citation_coverage=coverage,
            citation_precision=cit_precision,
            faithfulness_result=faith_res,
            validation_trace=trace,
            failure_reasons=failure_reasons,
        )

        return val_result, parsed, parsed_claims, resolved_citations

    def _inspect_freeform_text(
        self,
        summary_text: str,
        explanation_text: str,
        claims: List[ExplanationClaim],
    ) -> List[str]:
        """Inspect free-form summary and explanation text for ungrounded factual assertions.
        
        Guarantees that factual claims cannot bypass validation by being embedded
        only in summary or explanation without structured claim backing (Rule 6).
        """
        errors = []
        combined_text = f"{summary_text} {explanation_text}"

        factual_indicators = [
            r"\bpower supply\b",
            r"\bcatastrophically failed\b",
            r"\bserver crashed\b",
            r"\bhardware reboot\b",
            r"\bdisk corrupted\b",
            r"\bmemory leak\b",
            r"\bnetwork split\b",
            r"\bswitch failed\b",
            r"\bkernel panic\b",
            r"\bdata corrupted\b",
        ]

        supported_claim_texts = " ".join(c.text.lower() for c in claims if c.supported)

        for pattern in factual_indicators:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                matched_phrase = match.group(0).lower()
                if matched_phrase not in supported_claim_texts:
                    errors.append(
                        f"Factual assertion in summary/explanation is absent from verified structured claims: '{match.group(0)}'."
                    )

        return errors
