"""FastAPI application factory for SentinelLog Serving Layer."""

import logging
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sentinellog.serving.api.routes import api_router
from sentinellog.serving.config import ServingConfig, get_default_config
from sentinellog.serving.errors.handlers import register_exception_handlers
from sentinellog.serving.middleware.request_id import RequestIdMiddleware
from sentinellog.serving.middleware.security import SecurityHeadersMiddleware
from sentinellog.serving.version import (
    API_DESCRIPTION,
    API_TITLE,
    SERVING_VERSION,
)


def create_app(config: Optional[ServingConfig] = None) -> FastAPI:
    """Instantiate and configure FastAPI serving application.
    
    Args:
        config: Optional ServingConfig instance. If None, loaded from environment/YAML.
        
    Returns:
        Configured FastAPI application instance.
    """
    cfg = config or get_default_config()

    # Configure root logging level
    log_level = getattr(logging, cfg.server.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=SERVING_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. CORS Configuration (Explicit origins, no wildcard default)
    if cfg.server.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.server.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    # 2. Security Headers & Payload Size Middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        max_request_bytes=cfg.server.max_request_bytes,
    )

    # 3. Request ID & Structured Logging Middleware
    app.add_middleware(RequestIdMiddleware)

    # 4. Centralized Exception Handlers
    register_exception_handlers(app)

    # 5. API Routes
    app.include_router(api_router)

    return app


# Module-level default application instance for ASGI servers
app = create_app()
