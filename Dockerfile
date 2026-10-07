# ==============================================================================
# SentinelLog Production Containerfile (Hardened)
# ==============================================================================
# Multi-stage build with non-root runtime execution, minimal package footprint,
# read-only root compatibility, and zero baked-in secrets.

FROM python:3.12-slim-bookworm AS builder

# Set build environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /install

# Install build dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install/deps --no-warn-script-location -r requirements.txt

# ------------------------------------------------------------------------------
# Final Hardened Runtime Stage
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="SentinelLog Security Team" \
      description="Calibrated Selective Prediction for LLM-Assisted Incident Triage" \
      version="0.14.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SENTINELLOG_AUTH_ENABLED=true \
    SENTINELLOG_DEBUG=false \
    SENTINELLOG_ENFORCE_PRODUCTION_MODE=true \
    PATH="/app/deps/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Security hardening: Create unprivileged system user and group (UID/GID 10001)
RUN groupadd -g 10001 sentinels && \
    useradd -u 10001 -g sentinels -s /sbin/nologin -M sentinellog && \
    mkdir -p /app /app/data /app/results /app/configs /tmp/sentinellog && \
    chown -R sentinellog:sentinels /app /tmp/sentinellog && \
    chmod 1777 /tmp/sentinellog

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder --chown=sentinellog:sentinels /install/deps /app/deps

# Copy application source code and configuration
COPY --chown=sentinellog:sentinels sentinellog/ /app/sentinellog/
COPY --chown=sentinellog:sentinels configs/ /app/configs/
COPY --chown=sentinellog:sentinels results/ /app/results/
COPY --chown=sentinellog:sentinels data/ /app/data/

# Switch to non-root user
USER 10001:10001

# Expose internal listening port
EXPOSE 8000

# Health check using standard python urllib against liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1

# Execute serving application via uvicorn
ENTRYPOINT ["uvicorn", "sentinellog.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
