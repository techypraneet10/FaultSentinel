"""Safe process diagnostics, candidate SLI definitions, and system information."""

import os
import sys
import time
from typing import Any, Dict

from sentinellog.observability.config import get_observability_config
from sentinellog.observability.metrics import get_metrics_registry

API_TITLE = "SentinelLog Serving API"
API_VERSION = "v1"
SERVING_VERSION = "0.10.0"

_PROCESS_START_TIME = time.time()


def get_process_uptime_seconds() -> float:
    """Return process uptime in seconds."""
    return round(time.time() - _PROCESS_START_TIME, 2)


def get_safe_diagnostics() -> Dict[str, Any]:
    """Retrieve operational diagnostics without exposing filesystem paths, credentials, or env vars."""
    cfg = get_observability_config()
    uptime_sec = get_process_uptime_seconds()

    # Attempt to read memory usage via standard libraries if available
    memory_info: Dict[str, Any] = {"status": "NOT_AVAILABLE"}
    try:
        import resource  # Available on POSIX
        usage = resource.getrusage(resource.RUSAGE_SELF)
        memory_info = {
            "max_rss_kb": usage.ru_maxrss,
            "status": "AVAILABLE",
        }
    except Exception:
        # Windows or non-resource platform
        memory_info = {"status": "NOT_AVAILABLE"}

    return {
        "service": cfg.observability.service_name,
        "environment": cfg.observability.environment,
        "api_title": API_TITLE,
        "api_version": API_VERSION,
        "serving_version": SERVING_VERSION,
        "pipeline_version": "13.0.0",
        "python_version": sys.version.split()[0],
        "uptime_seconds": uptime_sec,
        "observability": {
            "metrics_enabled": cfg.metrics.enabled,
            "tracing_enabled": cfg.tracing.enabled,
            "json_logging_enabled": cfg.observability.json_logging,
            "redaction_enabled": cfg.observability.redaction_enabled,
            "tracing_exporter": cfg.tracing.exporter,
            "sample_rate": cfg.tracing.sample_rate,
        },
        "process_resources": {
            "memory": memory_info,
            "cpu": {"status": "NOT_AVAILABLE"},
        },
    }


def get_candidate_slis() -> Dict[str, Any]:
    """Calculate observed operational SLIs from in-memory metrics without fabricated target claims."""
    reg = get_metrics_registry()

    req_cnt = reg.get_counter("request_count")
    req_err = reg.get_counter("request_errors")
    an_cnt = reg.get_counter("analysis_count")

    total_requests = 0.0
    total_errors = 0.0
    if req_cnt:
        for val in req_cnt._values.values():
            total_requests += val
    if req_err:
        for val in req_err._values.values():
            total_errors += val

    req_success_rate = 1.0 if total_requests == 0 else max(0.0, (total_requests - total_errors) / total_requests)

    total_analyses = 0.0
    if an_cnt:
        for val in an_cnt._values.values():
            total_analyses += val

    auto_clear = reg.get_counter("auto_clear_count")
    escalate = reg.get_counter("escalation_count")

    tot_ac = sum(auto_clear._values.values()) if auto_clear else 0.0
    tot_esc = sum(escalate._values.values()) if escalate else 0.0
    tot_gated = tot_ac + tot_esc
    escalation_rate = (tot_esc / tot_gated) if tot_gated > 0 else 0.0

    return {
        "candidate_slis": {
            "request_success_rate": round(req_success_rate, 4),
            "total_requests_observed": int(total_requests),
            "total_analyses_observed": int(total_analyses),
            "total_escalated_observed": int(tot_esc),
            "total_auto_cleared_observed": int(tot_ac),
            "observed_escalation_rate": round(escalation_rate, 4),
        },
        "notice": "Values represent observed telemetry metrics, not target or guaranteed SLO values.",
    }
