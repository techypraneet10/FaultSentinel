"""Analysis and API root metadata endpoints."""

from fastapi import APIRouter, Depends, status

from sentinellog.serving.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    RootMetadataResponse,
)
from sentinellog.serving.dependencies import get_analysis_service, get_request_id
from sentinellog.serving.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.get(
    "",
    response_model=RootMetadataResponse,
    summary="Root Service Metadata",
    description="Returns public API versioning and service status without exposing internal paths or secrets.",
)
async def api_root() -> RootMetadataResponse:
    """Return public API status and build metadata."""
    return RootMetadataResponse()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Log Sequence",
    description=(
        "Executes bounded log incident triage across Phase 8 deterministic reasoning "
        "and Phase 9 citation-grounded LLM explanation. Preserves authoritative Phase 8 decisions."
    ),
)
async def analyze_logs(
    request: AnalyzeRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    request_id: str = Depends(get_request_id),
) -> AnalyzeResponse:
    """Submit a bounded log sequence for triage and explanation."""
    return await analysis_service.analyze(request=request, request_id=request_id)
