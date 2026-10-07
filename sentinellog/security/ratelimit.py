"""In-memory sliding window rate limiter with bounded cardinality and trusted proxy validation."""

import collections
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple
from starlette.requests import Request

from sentinellog.security.config import get_security_config

logger = logging.getLogger("sentinellog.security.ratelimit")

# Max distinct rate limit keys kept in memory to prevent memory exhaustion attacks
MAX_TRACKED_CLIENTS = 10000


class RateLimiter:
    """Bounded, thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # client_key -> deque of timestamps
        self._history: Dict[str, collections.deque] = {}

    def extract_client_identifier(self, request: Request, trusted_proxies: List[str]) -> str:
        """Derive bounded client identity from Authorization token or validated IP."""
        # 1. Prefer authenticated token identity (hashed prefix or token)
        auth_header = request.headers.get("Authorization")
        if auth_header and "bearer" in auth_header.lower():
            # Bound key to fixed length
            token = auth_header.strip().split()[-1]
            return f"auth:{token[:16]}"

        # 2. Extract IP address with strict proxy validation
        client_host = request.client.host if request.client else "127.0.0.1"

        # Check if direct peer is a trusted proxy
        if client_host in trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Leftmost is the originating client
                first_ip = forwarded.split(",")[0].strip()
                return f"ip:{first_ip}"

        return f"ip:{client_host}"

    def check_rate_limit(self, client_key: str) -> Tuple[bool, int]:
        """Check if client request is within rate limits.
        
        Returns:
            (is_allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Memory safety: if too many unique keys tracked, prune stale entries
            if len(self._history) >= MAX_TRACKED_CLIENTS:
                stale_keys = [k for k, q in self._history.items() if not q or q[-1] < cutoff]
                for k in stale_keys:
                    del self._history[k]
                # If still at cap, evict oldest
                if len(self._history) >= MAX_TRACKED_CLIENTS:
                    oldest_key = next(iter(self._history))
                    del self._history[oldest_key]

            if client_key not in self._history:
                self._history[client_key] = collections.deque()

            q = self._history[client_key]

            # Pop expired timestamps
            while q and q[0] < cutoff:
                q.popleft()

            if len(q) >= self.max_requests:
                # Oldest timestamp in current window determines retry_after
                retry_after = max(1, int(q[0] + self.window_seconds - now))
                return False, retry_after

            q.append(now)
            return True, 0

    def reset(self) -> None:
        """Clear all tracked histories."""
        with self._lock:
            self._history.clear()


_GLOBAL_RATE_LIMITER: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Retrieve or initialize global RateLimiter singleton."""
    global _GLOBAL_RATE_LIMITER
    if _GLOBAL_RATE_LIMITER is None:
        cfg = get_security_config()
        _GLOBAL_RATE_LIMITER = RateLimiter(
            max_requests=cfg.rate_limit_requests,
            window_seconds=cfg.rate_limit_window_seconds,
        )
    return _GLOBAL_RATE_LIMITER


def reset_rate_limiter() -> None:
    """Reset global rate limiter instance."""
    global _GLOBAL_RATE_LIMITER
    if _GLOBAL_RATE_LIMITER is not None:
        _GLOBAL_RATE_LIMITER.reset()
    _GLOBAL_RATE_LIMITER = None
