"""Request ID tracing middleware and structured request logging."""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("sentinellog.serving.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates unique request IDs and logs structured access records."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check incoming X-Request-ID header or generate secure UUID4
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and len(incoming_id) <= 128 and incoming_id.replace("-", "").isalnum():
            request_id = incoming_id
        else:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id

        # Structured access log without logging sensitive payloads or secrets
        logger.info(
            f"method={request.method} path={request.url.path} status={response.status_code} "
            f"duration_ms={duration_ms} request_id={request_id}"
        )

        return response
