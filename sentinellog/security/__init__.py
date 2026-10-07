"""SentinelLog Security & Production Hardening Package."""

from sentinellog.security.auth import (
    AuthenticationResult,
    authenticate_request,
    extract_bearer_token,
    verify_api_key,
)
from sentinellog.security.config import (
    SecurityConfig,
    get_security_config,
    reset_security_config,
)
from sentinellog.security.middleware import SecurityHardeningMiddleware
from sentinellog.security.paths import (
    PathTraversalError,
    PathValidator,
    get_path_validator,
    safe_resolve_path,
)
from sentinellog.security.ratelimit import (
    RateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)
from sentinellog.security.secret_scanner import scan_repository, scan_text

__all__ = [
    "SecurityConfig",
    "get_security_config",
    "reset_security_config",
    "AuthenticationResult",
    "authenticate_request",
    "extract_bearer_token",
    "verify_api_key",
    "SecurityHardeningMiddleware",
    "PathTraversalError",
    "PathValidator",
    "get_path_validator",
    "safe_resolve_path",
    "RateLimiter",
    "get_rate_limiter",
    "reset_rate_limiter",
    "scan_text",
    "scan_repository",
]
