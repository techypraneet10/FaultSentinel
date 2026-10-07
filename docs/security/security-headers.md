# SentinelLog HTTP Security Headers & Browser Hardening (Phase 14)

## 1. Overview

SentinelLog enforces standard HTTP defense-in-depth headers on all responses emitted by the serving layer. These headers protect browser clients against MIME-sniffing, framing/clickjacking, referrer leakage, and unauthorized script injection.

## 2. Implemented Security Headers

| Header | Configured Value | Rationale |
| :--- | :--- | :--- |
| `X-Content-Type-Options` | `nosniff` | Prevents browsers from MIME-sniffing responses away from declared content-type, blocking script execution masquerading as text. |
| `X-Frame-Options` | `DENY` | Completely prohibits rendering SentinelLog inside `<frame>`, `<iframe>`, `<embed>`, or `<object>` elements, preventing clickjacking attacks. |
| `Referrer-Policy` | `no-referrer` | Ensures no referrer headers are transmitted with outgoing browser navigation, protecting sensitive URLs and tokens from leaking. |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';` | Restricts resources to self origin. Permits inline styles required by React/Vite UI components while forbidding external script execution and framing. |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | **Conditional emission**: Only sent when `request.url.scheme == "https"`. Never sent over plain HTTP local development. |

## 3. Frontend Compatibility (Phase 11 Preservation)

The Content Security Policy policy is specifically designed to remain 100% compatible with the Phase 11 Operator Dashboard:
- Allows internal Vite bundle script execution (`'self'`).
- Allows CSS-in-JS style injection (`'unsafe-inline'`).
- Allows data URIs for embedded badge assets (`img-src 'self' data:`).
- Forbids external remote scripts, framing, and untrusted network connections.
