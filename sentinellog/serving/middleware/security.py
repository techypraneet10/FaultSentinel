"""Security headers and payload size protection middleware."""

import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies defense-in-depth HTTP security headers and bounds payload bytes."""

    def __init__(self, app, max_request_bytes: int = 1048576):
        super().__init__(app)
        self.max_request_bytes = max_request_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check Content-Length header against maximum allowed payload size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length_val = int(content_length)
                if length_val > self.max_request_bytes:
                    req_id = getattr(request.state, "request_id", "unknown")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body length ({length_val} bytes) exceeds maximum permitted limit ({self.max_request_bytes} bytes).",
                                "request_id": req_id,
                                "details": {"max_bytes": self.max_request_bytes, "received_bytes": length_val},
                            }
                        },
                        headers={"X-Request-ID": req_id},
                    )
            except ValueError:
                pass

        response = await call_next(request)

        # Standard defense-in-depth security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        return response
