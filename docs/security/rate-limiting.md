# SentinelLog Sliding Window Rate Limiting (Phase 14)

## 1. Overview

To protect against Denial of Service (DoS), brute-force authentication attacks, and resource exhaustion, SentinelLog incorporates an in-memory, thread-safe sliding window rate limiter (`sentinellog.security.ratelimit.RateLimiter`).

## 2. Configuration Parameters

| Parameter | Env Override | Default | Description |
| :--- | :--- | :--- | :--- |
| `rate_limit_enabled` | `SENTINELLOG_RATE_LIMIT_ENABLED` | `true` | Enables sliding window throttling. |
| `rate_limit_requests` | `SENTINELLOG_RATE_LIMIT_REQUESTS` | `120` | Maximum allowed requests per window. |
| `rate_limit_window_seconds` | `SENTINELLOG_RATE_LIMIT_WINDOW_SECONDS` | `60` | Length of the sliding observation window. |
| `trusted_proxies` | `SENTINELLOG_TRUSTED_PROXIES` | `127.0.0.1, ::1` | Reverse proxy IPs authorized to forward client addresses. |

## 3. Client Identity Extraction & Proxy Security

Rate limiting keys are strictly derived to prevent spoofing:
1. **Authenticated Clients:** If a valid `Authorization: Bearer <token>` is present, the key is derived from a bounded prefix `auth:<token[:16]>`.
2. **Unauthenticated / Fallback Clients:** Client IP address is extracted:
   - If the direct peer is in `trusted_proxies`, SentinelLog examines the first entry in `X-Forwarded-For`.
   - If the direct peer is **not** in `trusted_proxies`, `X-Forwarded-For` is ignored and the direct socket IP is used. This prevents arbitrary attackers from bypassing rate limits by faking forwarded headers.

## 4. Memory Safety & Bounded Cardinality

To defend against state-exhaustion memory attacks where an attacker floods the server with millions of spoofed IP addresses:
- The rate limiter enforces a hard cap of `MAX_TRACKED_CLIENTS = 10000`.
- When the history table reaches capacity, expired and stale client timestamps are automatically pruned under a lock.
- If still saturated, the oldest entry is evicted, ensuring total memory consumption remains strictly O(1) bounded.

## 5. Throttling Response (HTTP 429)

When a client exceeds the permitted threshold, the server returns **HTTP 429 Too Many Requests**:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please wait 14 seconds before retrying.",
    "request_id": "req-830219",
    "details": {
      "retry_after_seconds": 14
    }
  }
}
```

The response includes the standard `Retry-After: <seconds>` HTTP header. Rate limit breaches increment the `rate_limit_exceeded_total` counter.
