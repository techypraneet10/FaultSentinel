"""FastAPI dependency injection providers."""

from typing import Optional
from fastapi import Depends, Request

from sentinellog.serving.config import ServingConfig, get_default_config
from sentinellog.serving.services.analysis_service import AnalysisService
from sentinellog.serving.services.pipeline_service import PipelineService

_pipeline_service_instance: Optional[PipelineService] = None


def get_config() -> ServingConfig:
    """Retrieve serving configuration."""
    return get_default_config()


def get_pipeline_service(
    config: ServingConfig = Depends(get_config),
) -> PipelineService:
    """Retrieve or initialize shared PipelineService singleton."""
    global _pipeline_service_instance
    if _pipeline_service_instance is None:
        _pipeline_service_instance = PipelineService(config=config)
    return _pipeline_service_instance


def get_analysis_service(
    config: ServingConfig = Depends(get_config),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
) -> AnalysisService:
    """Retrieve AnalysisService instance."""
    return AnalysisService(config=config, pipeline_service=pipeline_service)


def get_request_id(request: Request) -> str:
    """Retrieve request ID from request state."""
    req_id = getattr(request.state, "request_id", None)
    if not req_id:
        req_id = request.headers.get("X-Request-ID", "unknown")
    return str(req_id)
