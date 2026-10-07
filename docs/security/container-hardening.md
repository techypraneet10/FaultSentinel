# SentinelLog Container & Runtime Hardening (Phase 14)

## 1. Overview

SentinelLog provides a production-grade, hardened `Dockerfile` designed following minimal privilege and defense-in-depth principles.

## 2. Hardening Measures

### 2.1 Dedicated Non-Root User (Rule 36)
The container creates a dedicated unprivileged user and group:
```dockerfile
RUN groupadd -g 10001 sentinels && \
    useradd -u 10001 -g sentinels -s /sbin/nologin -M sentinellog
USER 10001:10001
```
The process runs entirely under UID `10001`, mitigating potential container breakout risks.

### 2.2 Minimal Base Image (Rule 39)
- Base Image: `python:3.12-slim-bookworm` (Debian Bookworm minimal footprint).
- Multi-stage build isolates compile-time tools (`build-essential`) in the builder stage, preventing compilation utilities from being present in the final runtime container.
- Package manager caches are completely purged (`rm -rf /var/lib/apt/lists/*`).

### 2.3 Filesystem Permissions & Read-Only Root (Rule 37)
- Application source (`/app/sentinellog`) is owned by `sentinellog:sentinels` with read-only operational permissions at runtime.
- Writable operations are restricted solely to `/tmp/sentinellog` (mode `1777`).
- In hardened deployment, the root filesystem can be mounted read-only (`--read-only`) with a tmpfs mount on `/tmp`.

### 2.4 Container Secrets (Rule 38)
- Zero build arguments (`ARG`) or environment variables contain real secrets.
- `.dockerignore` blocks `.env`, local keyrings, git history, and caches from entering the container context.

### 2.5 Health Check
Embedded container healthcheck executes an unprivileged Python urllib check against `/health/live`:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1
```
