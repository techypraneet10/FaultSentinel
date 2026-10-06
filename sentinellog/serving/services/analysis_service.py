"""Application analysis service orchestrating pipeline requests and building typed responses."""

import logging
import time
from typing import Any, Dict, List, Optional

from sentinellog.serving.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CitationResponse,
    ClaimResponse,
)
from sentinellog.serving.config import ServingConfig
from sentinellog.serving.errors.exceptions import (
    InvalidRequestError,
    PipelineServingError,
    UnsupportedDatasetError,
)
from sentinellog.serving.services.pipeline_service import PipelineService

logger = logging.getLogger("sentinellog.serving.analysis")


class AnalysisService:
    """Application-level service coordinating log analysis and response transformation."""

    def __init__(self, config: ServingConfig, pipeline_service: PipelineService):
        self.config = config
        self.pipeline_service = pipeline_service

    async def analyze(self, request: AnalyzeRequest, request_id: str) -> AnalyzeResponse:
        """Process bounded log analysis request and return validated AnalyzeResponse."""
        start_time = time.perf_counter()

        # 1. Dataset validation
        clean_ds = request.dataset.strip().lower()
        if clean_ds not in self.config.pipeline.supported_datasets:
            raise UnsupportedDatasetError(clean_ds)

        # 2. Extract options
        opts_dict: Dict[str, Any] = {}
        if request.options:
            opts_dict = request.options.model_dump(exclude_none=True)

        # 3. Invoke pipeline coordination
        try:
            assessment, bundle, exp = self.pipeline_service.process_analysis(
                dataset=clean_ds,
                logs=request.logs,
                options=opts_dict,
            )
        except Exception as e:
            if isinstance(e, (InvalidRequestError, UnsupportedDatasetError, PipelineServingError)):
                raise e
            logger.exception(f"Pipeline error during analysis (request_id={request_id}): {e}")
            raise PipelineServingError("Incident triage pipeline encountered an unrecoverable internal error.")

        # 4. Decision Immutability Invariant Verification (Rule 13)
        if exp.incident_decision != assessment.decision:
            raise PipelineServingError(
                f"Decision immutability invariant violated: explanation '{exp.incident_decision}' != assessment '{assessment.decision}'."
            )
        if exp.severity != assessment.severity:
            raise PipelineServingError(
                f"Severity immutability invariant violated: explanation '{exp.severity}' != assessment '{assessment.severity}'."
            )

        # 5. Build structured claim responses
        claims_out: List[ClaimResponse] = []
        for c in exp.claims:
            claims_out.append(
                ClaimResponse(
                    claim_id=c.claim_id,
                    claim_type=c.claim_type,
                    text=c.text,
                    citation_ids=c.citation_ids,
                    supported=c.supported,
                    support_score=c.support_score,
                )
            )

        # 6. Build safe citation responses without leaking raw server paths
        citations_out: List[CitationResponse] = []
        include_citations = request.options.include_citations if request.options else True
        include_raw = request.options.include_raw_excerpts if request.options else False

        if include_citations and bundle:
            for cit in bundle.citations:
                line_start = None
                line_end = None
                if cit.provenance and cit.provenance.source_location:
                    line_start = cit.provenance.source_location.line_start
                    line_end = cit.provenance.source_location.line_end

                citations_out.append(
                    CitationResponse(
                        citation_id=cit.citation_id,
                        dataset=cit.dataset,
                        split=cit.split,
                        source_window_id=cit.source_window_id,
                        line_start=line_start,
                        line_end=line_end,
                        citation_text=cit.citation_text if include_raw else None,
                    )
                )

        # 7. Extract evidence sufficiency from signals
        sufficiency_val = "SUFFICIENT"
        if assessment.reasoning_trace and assessment.reasoning_trace.signals:
            sig = assessment.reasoning_trace.signals.get("evidence_sufficiency")
            if sig:
                sufficiency_val = str(sig.get("value", "SUFFICIENT"))

        faithfulness_status = exp.faithfulness_status or "VERIFIED"

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        status_str = "abstention" if exp.explanation_status == "ABSTAINED" else "success"

        response = AnalyzeResponse(
            request_id=request_id,
            status=status_str,
            dataset=clean_ds,
            decision=assessment.decision,
            severity=assessment.severity,
            confidence=assessment.confidence,
            explanation_status=exp.explanation_status,
            summary=exp.summary,
            explanation=exp.explanation,
            claims=claims_out,
            citations=citations_out,
            evidence_sufficiency=sufficiency_val,
            provenance_status=assessment.provenance_status,
            faithfulness_status=faithfulness_status,
            processing_metadata={
                "duration_ms": duration_ms,
                "engine_version": assessment.engine_version,
                "model_name": exp.model_name,
                "log_records_processed": len(request.logs),
            },
        )

        return response
