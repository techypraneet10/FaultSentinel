"""Observability and diagnostics API endpoints for Phase 13."""

from typing import Any, Dict
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from sentinellog.observability.config import get_observability_config
from sentinellog.observability.diagnostics import get_candidate_slis, get_safe_diagnostics
from sentinellog.observability.metrics import get_metrics_registry

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus Metrics Exposition",
    description="Returns standard Prometheus text formatted operational metrics.",
)
async def metrics() -> PlainTextResponse:
    """Expose Prometheus formatted metrics."""
    registry = get_metrics_registry()
    exposition = registry.generate_exposition()
    return PlainTextResponse(content=exposition, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get(
    "/health/observability",
    summary="Observability Health Probe",
    description="Reports the operational status of logging, metrics, and tracing telemetry systems.",
)
async def health_observability() -> Dict[str, Any]:
    """Report status of observability components."""
    cfg = get_observability_config()
    return {
        "status": "ok",
        "telemetry": {
            "logging": "initialized" if cfg.observability.json_logging else "standard",
            "metrics": "initialized" if cfg.metrics.enabled else "disabled",
            "tracing": "initialized" if cfg.tracing.enabled else "disabled",
        },
    }


@router.get(
    "/api/v1/diagnostics",
    summary="Safe System Diagnostics",
    description="Returns bounded system metadata and candidate SLIs without leaking secrets or raw paths.",
)
async def get_diagnostics() -> Dict[str, Any]:
    """Retrieve safe operational diagnostics and observed candidate SLIs."""
    diag = get_safe_diagnostics()
    slis = get_candidate_slis()
    diag.update(slis)
    return diag
