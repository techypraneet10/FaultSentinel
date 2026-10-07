"""Distributed rate limiting abstraction supporting in-memory and Redis backends."""

import logging
import time
from typing import Optional, Tuple

from sentinellog.security.ratelimit import RateLimiter

logger = logging.getLogger("sentinellog.deployment.ratelimit")


class DistributedRateLimiter:
    """Rate limiter with configurable backend (in-memory or Redis) and graceful fallback."""

    def __init__(
        self,
        backend: str = "memory",
        max_requests: int = 120,
        window_seconds: int = 60,
        redis_url: Optional[str] = None,
        redis_client: Optional[object] = None,
    ):
        self.backend = backend
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_url = redis_url
        self._fallback_limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)
        self._redis = redis_client

        if self.backend == "redis" and self._redis is None and self.redis_url:
            self._init_redis()

    def _init_redis(self) -> None:
        """Attempt to initialize connection to Redis cluster."""
        try:
            import redis  # type: ignore
            self._redis = redis.Redis.from_url(self.redis_url, socket_timeout=2.0)
            # Test connectivity
            self._redis.ping()
            logger.info("Successfully connected to Redis for distributed rate limiting.")
        except Exception as e:
            logger.warning(
                f"Redis unavailable for distributed rate limiting ({e}). Failing safe to bounded in-memory limiter."
            )
            self._redis = None

    def check_rate_limit(self, client_key: str) -> Tuple[bool, int]:
        """Check rate limit against configured backend.
        
        Returns:
            (is_allowed: bool, retry_after_seconds: int)
        """
        if self.backend == "redis" and self._redis is not None:
            try:
                return self._check_redis(client_key)
            except Exception as e:
                logger.warning(f"Redis rate limit check failed ({e}). Falling back to memory limiter.")
                return self._fallback_limiter.check_rate_limit(client_key)

        # Default or fallback to local bounded in-memory limiter
        return self._fallback_limiter.check_rate_limit(client_key)

    def _check_redis(self, client_key: str) -> Tuple[bool, int]:
        """Sliding window atomic rate limit implementation via Redis zset."""
        now = time.time()
        cutoff = now - self.window_seconds
        key = f"sentinellog:ratelimit:{client_key}"

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        results = pipe.execute()

        current_count = results[1]
        oldest_entry = results[2]

        if current_count >= self.max_requests:
            retry_after = self.window_seconds
            if oldest_entry:
                oldest_ts = oldest_entry[0][1]
                retry_after = max(1, int(oldest_ts + self.window_seconds - now))
            return False, retry_after

        # Record current request timestamp
        pipe2 = self._redis.pipeline()
        pipe2.zadd(key, {str(now): now})
        pipe2.expire(key, self.window_seconds + 5)
        pipe2.execute()

        return True, 0

    def reset(self) -> None:
        """Reset state in both memory and redis if applicable."""
        self._fallback_limiter.reset()
        if self._redis is not None:
            try:
                self._redis.flushdb()
            except Exception:
                pass
