"""Constant-time token authentication and endpoint authorization verification."""

import hmac
import logging
from typing import Optional
from starlette.requests import Request

from sentinellog.security.config import get_security_config

logger = logging.getLogger("sentinellog.security.auth")


class AuthenticationResult:
    """Outcome of request authentication."""

    def __init__(self, authenticated: bool, error: Optional[str] = None, role: str = "anonymous"):
        self.authenticated = authenticated
        self.error = error
        self.role = role

def extract_bearer_token(request: Request) -> Optional[str]:
    """Safely extract bearer token from Authorization header or legacy X-API-Key."""
    auth_header = None
    api_key_header = None
    if hasattr(request, "headers") and request.headers:
        for k, v in request.headers.items():
            k_lower = k.lower()
            if k_lower == "authorization":
                auth_header = v
            elif k_lower == "x-api-key":
                api_key_header = v

    if auth_header:
        parts = auth_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

    # Legacy header fallback
    if api_key_header:
        return api_key_header.strip()

    return None


def verify_api_key(provided_token: Optional[str], expected_token: str) -> bool:
    """Perform constant-time comparison to prevent timing attacks."""
    if not provided_token or not expected_token:
        return False
    # Constant-time comparison using HMAC compare_digest
    return hmac.compare_digest(provided_token.encode("utf-8"), expected_token.encode("utf-8"))


def authenticate_request(request: Request) -> AuthenticationResult:
    """Evaluate request against configured authentication requirements.
    
    Protected endpoints:
      - /api/v1/analyze
      - /api/v1/diagnostics
      - /metrics (when auth enabled)

    Public/Operational endpoints:
      - /health/live (always public)
      - /health/ready (operational status)
      - /health/observability (operational status)
      - /docs, /redoc, /openapi.json (API docs)
    """
    config = get_security_config()

    # Public unauthenticated endpoints
    path = request.url.path
    if path == "/health/live":
        return AuthenticationResult(authenticated=True, role="public")

    # If auth is disabled (development mode), grant admin role across all endpoints
    if not config.auth_enabled:
        return AuthenticationResult(authenticated=True, role="admin")

    # In operational endpoints (/health/ready, /health/observability), allow without token if auth not strictly enforcing probe protection
    if path in ("/health/ready", "/health/observability", "/docs", "/redoc", "/openapi.json"):
        token = extract_bearer_token(request)
        if not token:
            return AuthenticationResult(authenticated=True, role="operator")

    token = extract_bearer_token(request)
    if not token:
        return AuthenticationResult(authenticated=False, error="authentication_required")

    # Check against configured keys (constant-time)
    if config.api_key and verify_api_key(token, config.api_key):
        return AuthenticationResult(authenticated=True, role="admin")
    if config.analyst_api_key and verify_api_key(token, config.analyst_api_key):
        return AuthenticationResult(authenticated=True, role="analyst")
    if config.operator_api_key and verify_api_key(token, config.operator_api_key):
        return AuthenticationResult(authenticated=True, role="operator")

    return AuthenticationResult(authenticated=False, error="invalid_credentials")


def authorize_request(role: str, path: str) -> tuple[bool, Optional[str]]:
    """Verify if authenticated role has permission to access the target path.
    
    Roles:
      - admin: unrestricted access
      - analyst: /api/v1/analyze, plus read health/docs
      - operator: /api/v1/diagnostics, /metrics, plus health/docs
      - public: /health/live
      
    Returns:
      (is_authorized: bool, error_reason: Optional[str])
    """
    if role == "admin":
        return True, None

    if path in ("/health/live", "/health/ready", "/health/observability", "/docs", "/redoc", "/openapi.json"):
        return True, None

    if path == "/api/v1/analyze":
        if role in ("analyst", "admin"):
            return True, None
        return False, "Endpoint requires 'analyst' or 'admin' role."

    if path in ("/api/v1/diagnostics", "/metrics"):
        if role in ("operator", "admin"):
            return True, None
        return False, "Endpoint requires 'operator' or 'admin' role."

    if path.startswith("/api/v1/fault-injection"):
        if role in ("operator", "admin"):
            return True, None
        return False, "Endpoint requires 'operator' or 'admin' role."

    if (
        path.startswith("/api/v1/replay")
        or path.startswith("/api/v1/evidence")
        or path.startswith("/api/v1/calibration")
        or path.startswith("/api/v1/incidents")
    ):
        if role in ("analyst", "operator", "admin"):
            return True, None
        return False, "Endpoint requires 'analyst', 'operator', or 'admin' role."

    return False, "Access denied for this role."
