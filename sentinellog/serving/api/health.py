"""Health and readiness probe endpoints."""

from fastapi import APIRouter, Depends, Response, status

from sentinellog.serving.api.schemas import HealthLiveResponse, HealthReadyResponse
from sentinellog.serving.dependencies import get_pipeline_service
from sentinellog.serving.services.pipeline_service import PipelineService

router = APIRouter(tags=["Health"])


@router.get(
    "/health/live",
    response_model=HealthLiveResponse,
    summary="Process Liveness Probe",
    description="Returns 200 OK if process is running. Performs no expensive checks.",
)
async def health_live() -> HealthLiveResponse:
    """Liveness probe confirming serving process is alive."""
    return HealthLiveResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    summary="Service Readiness Probe",
    description="Verifies that authoritative pipeline models and calibration assets are loaded.",
)
async def health_ready(
    response: Response,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
) -> HealthReadyResponse:
    """Readiness probe checking pipeline models and configuration."""
    is_ready = pipeline_service.is_ready()
    checks = {
        "configuration": "ok",
        "pipeline": "ok" if is_ready else "not_ready",
    }

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthReadyResponse(status="not_ready", checks=checks)

    return HealthReadyResponse(status="ready", checks=checks)
