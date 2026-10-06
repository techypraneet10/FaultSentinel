"""Main orchestration engine for Phase 9 LLM Explanation & Orchestration.

Coordinates:
1. Strict split protection and label leakage prevention (Rule 1 & Rule 34).
2. Provenance-gated execution ensuring zero calls on invalid provenance (Rule 49).
3. Bounded context construction and injection-resistant prompt building.
4. Safe LLM invocation with timeout and retry controls.
5. Strict fail-closed multi-stage validation and decision immutability enforcement.
6. Deterministic fallback / abstention handling.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from sentinellog.explanation.client import SafeLLMClient
from sentinellog.explanation.context import ExplanationContextBuilder
from sentinellog.explanation.exceptions import (
    InvalidSplitError,
    ProviderError,
    ProviderTimeoutError,
)
from sentinellog.explanation.fallback import FallbackHandler
from sentinellog.explanation.prompts import (
    SENTINELLOG_SYSTEM_PROMPT_V1,
    build_explanation_prompt,
)
from sentinellog.explanation.provider import BaseLLMProvider, MockLLMProvider, get_provider
from sentinellog.explanation.schemas import (
    ExplanationResult,
    ExplanationStatus,
    LLMUsageMetadata,
)
from sentinellog.explanation.validator import ExplanationValidator
from sentinellog.explanation.version import EXPLANATION_ENGINE_VERSION, PROMPT_VERSION
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.schemas import IncidentAssessment, ReasoningTrace
from sentinellog.scoring.artifacts import guard_no_test_split


def compute_configuration_hash(config: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint over canonical configuration dict."""
    canonical_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ExplanationOrchestrator:
    """High-level orchestrator generating grounded, citation-backed incident explanations."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        provider: Optional[BaseLLMProvider] = None,
        validator: Optional[ExplanationValidator] = None,
        context_builder: Optional[ExplanationContextBuilder] = None,
    ):
        self.config = config or {}
        self.config_hash = compute_configuration_hash(self.config) if self.config else "CONFIG_HASH_DEFAULT"

        # Instantiate provider and safe client
        if provider is not None:
            self.provider = provider
        else:
            self.provider = get_provider(self.config)

        client_cfg = self.config.get("client", {})
        self.client = SafeLLMClient(
            provider=self.provider,
            max_retries=client_cfg.get("max_retries", 2),
            timeout=client_cfg.get("timeout", 30.0),
            temperature=self.config.get("temperature", 0.0),
            max_tokens=self.config.get("max_tokens", 1000),
        )

        # Context builder & Validator
        self.context_builder = context_builder or ExplanationContextBuilder()
        self.validator = validator or ExplanationValidator(
            min_coverage=self.config.get("faithfulness_thresholds", {}).get("min_coverage", 0.50)
        )

    def explain(
        self,
        assessment: IncidentAssessment,
        citation_bundle: Optional[CitationBundle] = None,
        dataset: Optional[str] = None,
        split: str = "calibration",
        evidence: Optional[Any] = None,
        reasoning_trace: Optional[ReasoningTrace] = None,
        raw_excerpts: Optional[Dict[str, str]] = None,
        input_artifact_hashes: Optional[Dict[str, str]] = None,
    ) -> ExplanationResult:
        """Produce structured, grounded explanation for an incident assessment.
        
        Args:
            assessment: Deterministic Phase 8 IncidentAssessment.
            citation_bundle: Phase 7 verified CitationBundle.
            dataset: Dataset name ('hdfs' or 'bgl').
            split: Split name (strictly non-test).
            evidence: Optional Phase 6 evidence selections.
            reasoning_trace: Optional Phase 8 reasoning trace.
            raw_excerpts: Optional pre-loaded raw log lines.
            input_artifact_hashes: Dictionary of input file hashes.
            
        Returns:
            Fully populated, verified ExplanationResult.
        """
        ds = dataset or assessment.dataset
        clean_split = split.strip().lower()

        # Step 1: Split Guardrail (Rule 1)
        guard_no_test_split(clean_split)
        if clean_split == "test":
            raise InvalidSplitError("Rule 1 Violation: Cannot generate explanations on frozen test split.")

        # Step 2: Provenance Gate (Rule 49)
        # If provenance is invalid or unverified, abstain immediately without calling LLM
        if assessment.provenance_status != "VERIFIED":
            return FallbackHandler.create_fallback(
                assessment=assessment,
                reason=f"Provenance gate rejected window with provenance_status='{assessment.provenance_status}'.",
                status=ExplanationStatus.ABSTAINED,
                bundle=citation_bundle,
                config_hash=self.config_hash,
                input_artifact_hashes=input_artifact_hashes,
                model_name=getattr(self.provider, "model_name", "unknown"),
            )

        # Step 3: Build Context & Scan for Label Leakage (Rule 34)
        context = self.context_builder.build_context(
            assessment=assessment,
            citation_bundle=citation_bundle,
            raw_excerpts=raw_excerpts,
            split=clean_split,
        )

        # Step 4: Build Versioned, Injection-Resistant Prompt
        prompt = build_explanation_prompt(context)

        # Step 5: Invoke LLM Provider via Safe Client
        try:
            resp = self.client.execute(
                prompt=prompt,
                system_prompt=SENTINELLOG_SYSTEM_PROMPT_V1,
            )
        except (ProviderError, ProviderTimeoutError) as e:
            return FallbackHandler.create_fallback(
                assessment=assessment,
                reason=f"LLM Provider invocation error: {str(e)}",
                status=ExplanationStatus.PROVIDER_ERROR,
                bundle=citation_bundle,
                config_hash=self.config_hash,
                input_artifact_hashes=input_artifact_hashes,
                model_name=getattr(self.provider, "model_name", "unknown"),
            )

        # Step 6: Validate Output via ExplanationValidator
        val_res, parsed_json, parsed_claims, resolved_citations = self.validator.validate(
            raw_text=resp.text,
            assessment=assessment,
            bundle=citation_bundle,
            raw_excerpts=raw_excerpts,
        )

        # Step 7: Handle Validation Failures
        if not val_res.is_valid:
            failure_summary = "; ".join(val_res.failure_reasons)
            return FallbackHandler.create_fallback(
                assessment=assessment,
                reason=f"Validation pipeline rejected explanation: {failure_summary}",
                status=ExplanationStatus.VALIDATION_FAILED,
                bundle=citation_bundle,
                validation_trace=val_res.validation_trace,
                usage_metadata=resp.usage_metadata,
                config_hash=self.config_hash,
                input_artifact_hashes=input_artifact_hashes,
                model_name=resp.model_name,
            )

        # Step 8: Construct Successful ExplanationResult
        summary = str(parsed_json.get("summary", "")).strip()
        uncertainties = parsed_json.get("uncertainties", [])
        if not isinstance(uncertainties, list):
            uncertainties = []
        rec_action = parsed_json.get("recommended_action")

        # Synthesize full explanation narrative
        full_explanation = f"{summary}\n\nKey Claims:\n" + "\n".join(
            f"- [{c.claim_type}] {c.text} " + (" ".join(f"[{cid[:8]}...]" for cid in c.citation_ids) if c.citation_ids else "")
            for c in parsed_claims
        )
        if uncertainties:
            full_explanation += "\n\nUncertainties:\n" + "\n".join(f"- {u}" for u in uncertainties)
        if rec_action:
            full_explanation += f"\n\nRecommended Action:\n{rec_action}"

        exp_hash_seed = f"{assessment.window_id}:{ds}:{clean_split}:{resp.model_name}:{PROMPT_VERSION}"
        explanation_id = f"EXP-{hashlib.sha256(exp_hash_seed.encode('utf-8')).hexdigest()[:16]}"

        return ExplanationResult(
            explanation_id=explanation_id,
            dataset=ds,
            split=clean_split,
            window_id=assessment.window_id,
            incident_decision=assessment.decision,  # IMMUTABLE Phase 8 Decision
            severity=assessment.severity,          # IMMUTABLE Phase 8 Severity
            reasoning_confidence=assessment.confidence,
            summary=summary,
            explanation=full_explanation,
            claims=parsed_claims,
            citations=resolved_citations,
            uncertainties=uncertainties,
            recommended_action=rec_action,
            provenance_status=assessment.provenance_status,
            citation_validation_status=val_res.citation_status,
            faithfulness_status=val_res.faithfulness_result.status,
            explanation_status=ExplanationStatus.GENERATED.value,
            abstained=False,
            abstention_reason=None,
            model_name=resp.model_name,
            prompt_version=PROMPT_VERSION,
            explanation_engine_version=EXPLANATION_ENGINE_VERSION,
            input_artifact_hashes=input_artifact_hashes or {},
            configuration_hash=self.config_hash,
            validation_trace=val_res.validation_trace,
            usage_metadata=resp.usage_metadata,
            created_timestamp=None,
        )
