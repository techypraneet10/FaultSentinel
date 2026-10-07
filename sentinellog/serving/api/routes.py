"""Router aggregation for SentinelLog API."""

from fastapi import APIRouter

from sentinellog.serving.api.analysis import router as analysis_router
from sentinellog.serving.api.health import router as health_router
from sentinellog.serving.api.observability import router as observability_router
from sentinellog.serving.api.workbench import router as workbench_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(observability_router)
api_router.include_router(analysis_router)
api_router.include_router(workbench_router)
