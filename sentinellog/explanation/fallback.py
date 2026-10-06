"""Deterministic fallback and abstention engine for Phase 9.

Ensures:
1. Strict preservation of Phase 8 decision, severity, and confidence (Rule 27).
2. Deterministic structured ExplanationResult upon validation or provider failure.
3. Zero fabricated content during failure modes.
"""

from typing import Any, Dict, List, Optional

from sentinellog.explanation.schemas import (
    CitationValidationStatus,
    ExplanationClaim,
    ExplanationCitation,
    ExplanationResult,
    ExplanationStatus,
    FaithfulnessStatus,
    LLMUsageMetadata,
)
from sentinellog.explanation.version import EXPLANATION_ENGINE_VERSION, PROMPT_VERSION
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.schemas import IncidentAssessment


class FallbackHandler:
    """Creates deterministic abstention or fallback explanation records."""

    @staticmethod
    def create_fallback(
        assessment: IncidentAssessment,
        reason: str,
        status: ExplanationStatus = ExplanationStatus.ABSTAINED,
        bundle: Optional[CitationBundle] = None,
        validation_trace: Optional[List[Dict[str, Any]]] = None,
        usage_metadata: Optional[LLMUsageMetadata] = None,
        config_hash: str = "CONFIG_HASH_UNSET",
        input_artifact_hashes: Optional[Dict[str, str]] = None,
        model_name: str = "deterministic-fallback",
        created_timestamp: Optional[str] = None,
    ) -> ExplanationResult:
        """Construct fallback ExplanationResult preserving Phase 8 deterministic invariants.
        
        Args:
            assessment: Authoritative Phase 8 assessment.
            reason: Explanation of why generation fell back or abstained.
            status: Lifecycle status of the explanation.
            bundle: Optional Phase 7 citation bundle.
            validation_trace: Validation steps executed before failure.
            usage_metadata: Runtime tokens / latency if provider was invoked.
            config_hash: Canonical configuration SHA-256.
            input_artifact_hashes: Input files SHA-256.
            model_name: Model identifier.
            created_timestamp: Optional creation timestamp.
            
        Returns:
            Grounded ExplanationResult marking abstention.
        """
        explanation_id = f"EXP-{assessment.window_id[:20]}-ABSTAINED"

        summary = (
            f"Explanation abstained due to: {reason}. "
            f"Authoritative deterministic triage decision: {assessment.decision} "
            f"(Severity: {assessment.severity}, Confidence: {assessment.confidence:.2f})."
        )

        detailed_explanation = (
            f"The LLM explanation layer declined to produce an ungrounded or contradictory narrative. "
            f"The upstream deterministic reasoning engine determined this window to be '{assessment.decision}' "
            f"with '{assessment.severity}' severity based on signal agreement and evidence sufficiency. "
            f"Abstention trigger: {reason}"
        )

        # Convert available citations
        citations: List[ExplanationCitation] = []
        if bundle and bundle.citations:
            for cit in bundle.citations:
                loc_dict = cit.provenance.source_location.to_dict() if cit.provenance else {}
                citations.append(
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
                        provenance_status=cit.provenance.source_artifact.dataset if cit.provenance else "UNKNOWN",
                        source_location=loc_dict,
                    )
                )

        return ExplanationResult(
            explanation_id=explanation_id,
            dataset=assessment.dataset,
            split=assessment.split,
            window_id=assessment.window_id,
            incident_decision=assessment.decision,  # PRESERVED EXACTLY
            severity=assessment.severity,          # PRESERVED EXACTLY
            reasoning_confidence=assessment.confidence,
            summary=summary,
            explanation=detailed_explanation,
            claims=[],
            citations=citations,
            uncertainties=[f"Explanation narrative was abstained: {reason}"],
            recommended_action="Inspect deterministic signals and raw logs directly.",
            provenance_status=assessment.provenance_status,
            citation_validation_status=CitationValidationStatus.UNCHECKED.value,
            faithfulness_status=FaithfulnessStatus.NOT_EVALUATED.value,
            explanation_status=status.value,
            abstained=True,
            abstention_reason=reason,
            model_name=model_name,
            prompt_version=PROMPT_VERSION,
            explanation_engine_version=EXPLANATION_ENGINE_VERSION,
            input_artifact_hashes=input_artifact_hashes or {},
            configuration_hash=config_hash,
            validation_trace=validation_trace or [],
            usage_metadata=usage_metadata,
            created_timestamp=created_timestamp,
        )
