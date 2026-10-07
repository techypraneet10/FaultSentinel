"""Defense-in-depth security middleware enforcing authentication, rate limiting, and security headers."""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from sentinellog.observability.logging import emit_event
from sentinellog.observability.metrics import get_metrics_registry
from sentinellog.security.auth import authenticate_request, authorize_request
from sentinellog.security.config import get_security_config
from sentinellog.security.ratelimit import get_rate_limiter

logger = logging.getLogger("sentinellog.security")


class SecurityHardeningMiddleware(BaseHTTPMiddleware):
    """Enforces request limits, rate limits, API authentication, and security headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        config = get_security_config()
        registry = get_metrics_registry()
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "unknown")

        # Allow CORS preflight requests to pass through cleanly to CORSMiddleware
        if request.method == "OPTIONS":
            return await call_next(request)

        # 1. Request Body Size Protection (Early rejection before parsing body)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length_val = int(content_length)
                if length_val > config.max_request_bytes:
                    try:
                        registry.get_counter("request_errors").inc(1.0, endpoint="security", status="failure")
                    except Exception:
                        pass
                    emit_event(
                        logger,
                        logging.WARNING,
                        "request_rejected",
                        message=f"Request payload {length_val} bytes exceeds limit {config.max_request_bytes}",
                        request_id=req_id,
                        error_code="PAYLOAD_TOO_LARGE",
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body length ({length_val} bytes) exceeds maximum permitted limit ({config.max_request_bytes} bytes).",
                                "request_id": req_id,
                                "details": {"max_bytes": config.max_request_bytes, "received_bytes": length_val},
                            }
                        },
                        headers={"X-Request-ID": req_id},
                    )
            except ValueError:
                pass

        # 2. Rate Limiting Check
        if config.rate_limit_enabled:
            limiter = get_rate_limiter()
            client_id = limiter.extract_client_identifier(request, config.trusted_proxies)
            is_allowed, retry_after = limiter.check_rate_limit(client_id)
            if not is_allowed:
                try:
                    registry.get_counter("rate_limit_exceeded_total").inc(1.0)
                    registry.get_counter("request_errors").inc(1.0, endpoint="security", status="failure")
                except Exception:
                    pass
                emit_event(
                    logger,
                    logging.WARNING,
                    "rate_limit_exceeded",
                    message="Rate limit threshold exceeded",
                    request_id=req_id,
                    error_code="RATE_LIMIT_EXCEEDED",
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Please wait {retry_after} seconds before retrying.",
                            "request_id": req_id,
                            "details": {"retry_after_seconds": retry_after},
                        }
                    },
                    headers={"X-Request-ID": req_id, "Retry-After": str(retry_after)},
                )

        # 3. Authentication & Authorization Check
        auth_res = authenticate_request(request)
        if not auth_res.authenticated:
            try:
                registry.get_counter("authentication_failures_total").inc(1.0)
                registry.get_counter("request_errors").inc(1.0, endpoint="security", status="failure")
            except Exception:
                pass
            emit_event(
                logger,
                logging.WARNING,
                "authentication_failed",
                message=f"Authentication failed: {auth_res.error}",
                request_id=req_id,
                error_code="AUTHENTICATION_FAILED",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Valid API key or Bearer token required for access.",
                        "request_id": req_id,
                        "details": {"reason": auth_res.error},
                    }
                },
                headers={"X-Request-ID": req_id},
            )

        # Save verified auth role to request state
        request.state.auth_role = auth_res.role

        # 4. Role Authorization Check
        is_authz, authz_err = authorize_request(auth_res.role, request.url.path)
        if not is_authz:
            try:
                registry.get_counter("authorization_denials_total").inc(1.0)
                registry.get_counter("request_errors").inc(1.0, endpoint="security", status="failure")
            except Exception:
                pass
            emit_event(
                logger,
                logging.WARNING,
                "authorization_denied",
                message=f"Authorization denied for role '{auth_res.role}': {authz_err}",
                request_id=req_id,
                error_code="FORBIDDEN",
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": authz_err or "Insufficient permissions for this endpoint.",
                        "request_id": req_id,
                        "details": {"role": auth_res.role},
                    }
                },
                headers={"X-Request-ID": req_id},
            )

        # 5. Invoke Next Middleware / Handler
        response = await call_next(request)

        # 6. Security Response Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        # Content Security Policy (permitting Phase 11 dashboard script & style requirements)
        csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';"
        response.headers["Content-Security-Policy"] = csp

        # HSTS only when HTTPS is actually used
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
