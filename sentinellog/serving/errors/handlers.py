"""Centralized FastAPI exception handlers."""

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sentinellog.serving.errors.exceptions import SentinelLogServingError

logger = logging.getLogger("sentinellog.serving")


def _get_request_id(request: Request) -> str:
    """Safely retrieve request ID from request state or headers."""
    req_id = getattr(request.state, "request_id", None)
    if not req_id:
        req_id = request.headers.get("X-Request-ID", "unknown")
    return str(req_id)


def _format_error_response(
    code: str,
    message: str,
    request_id: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Build standardized, typed error response structure."""
    content = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        }
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Request-ID": request_id},
    )


async def sentinellog_error_handler(request: Request, exc: SentinelLogServingError) -> JSONResponse:
    """Handle domain SentinelLogServingError exceptions."""
    req_id = _get_request_id(request)
    logger.warning(
        f"Domain exception [{exc.code}] on {request.method} {request.url.path} (request_id={req_id}): {exc.message}"
    )
    return _format_error_response(
        code=exc.code,
        message=exc.message,
        request_id=req_id,
        status_code=exc.status_code,
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic/FastAPI input validation errors."""
    req_id = _get_request_id(request)
    error_details = []
    has_unsupported_dataset = False

    for err in exc.errors():
        loc = ".".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_details.append({"loc": loc, "msg": msg, "type": err.get("type")})
        if "dataset" in loc and ("literal_error" in str(err.get("type")) or "value_error" in str(err.get("type"))):
            has_unsupported_dataset = True

    code = "UNSUPPORTED_DATASET" if has_unsupported_dataset else "INVALID_REQUEST"
    message = "Request validation failed. Verify request body parameters." if not has_unsupported_dataset else "Requested dataset is unsupported."

    logger.info(f"Validation failure on {request.method} {request.url.path} (request_id={req_id}): {error_details}")
    try:
        from sentinellog.observability.metrics import get_metrics_registry
        get_metrics_registry().get_counter("request_validation_failures_total").inc(1.0, endpoint=request.url.path)
    except Exception:
        pass
    return _format_error_response(
        code=code,
        message=message,
        request_id=req_id,
        status_code=422,
        details={"validation_errors": error_details},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPExceptions."""
    req_id = _get_request_id(request)
    code_map = {
        400: "INVALID_REQUEST",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        422: "INVALID_REQUEST",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    logger.info(f"HTTP exception [{exc.status_code}] on {request.method} {request.url.path} (request_id={req_id}): {exc.detail}")
    return _format_error_response(
        code=code,
        message=str(exc.detail),
        request_id=req_id,
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled internal exceptions without leaking stack traces or internal secrets."""
    req_id = _get_request_id(request)
    logger.exception(f"Unhandled exception on {request.method} {request.url.path} (request_id={req_id}): {exc}")
    return _format_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected internal server error occurred.",
        request_id=req_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers onto FastAPI instance."""
    app.add_exception_handler(SentinelLogServingError, sentinellog_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
