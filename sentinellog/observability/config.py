"""Configuration data structures and loaders for SentinelLog Observability."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class ObservabilitySection(BaseModel):
    service_name: str = "sentinellog"
    environment: str = "development"
    log_level: str = "INFO"
    json_logging: bool = True
    redaction_enabled: bool = True


class MetricsSection(BaseModel):
    enabled: bool = True
    endpoint: str = "/metrics"
    export_process_metrics: bool = True


class TracingSection(BaseModel):
    enabled: bool = True
    sample_rate: float = 1.0
    exporter: str = "in_memory"
    max_buffer_size: int = 1000
    otlp_endpoint: Optional[str] = None


class ReliabilitySection(BaseModel):
    request_timeout_sec: float = 30.0
    llm_timeout_sec: float = 15.0
    max_retries: int = 2
    fail_closed: bool = True


class ObservabilityConfig(BaseModel):
    observability: ObservabilitySection = Field(default_factory=ObservabilitySection)
    metrics: MetricsSection = Field(default_factory=MetricsSection)
    tracing: TracingSection = Field(default_factory=TracingSection)
    reliability: ReliabilitySection = Field(default_factory=ReliabilitySection)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ObservabilityConfig":
        """Load configuration from YAML file and apply SENTINELLOG_ environment overrides."""
        cfg_dict: Dict[str, Any] = {}
        target_path = config_path or os.getenv("SENTINELLOG_CONFIG_PATH", "configs/phase13.yaml")
        p = Path(target_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    cfg_dict = loaded

        inst = cls(**cfg_dict)

        # Apply SENTINELLOG_ environment variables
        if os.getenv("SENTINELLOG_LOG_LEVEL"):
            inst.observability.log_level = os.environ["SENTINELLOG_LOG_LEVEL"]
        if os.getenv("SENTINELLOG_JSON_LOGGING"):
            inst.observability.json_logging = os.environ["SENTINELLOG_JSON_LOGGING"].lower() in ("true", "1", "yes")
        if os.getenv("SENTINELLOG_METRICS_ENABLED"):
            inst.metrics.enabled = os.environ["SENTINELLOG_METRICS_ENABLED"].lower() in ("true", "1", "yes")
        if os.getenv("SENTINELLOG_TRACING_ENABLED"):
            inst.tracing.enabled = os.environ["SENTINELLOG_TRACING_ENABLED"].lower() in ("true", "1", "yes")
        if os.getenv("SENTINELLOG_OTLP_ENDPOINT"):
            inst.tracing.otlp_endpoint = os.environ["SENTINELLOG_OTLP_ENDPOINT"]
        if os.getenv("SENTINELLOG_TRACE_SAMPLE_RATE"):
            try:
                inst.tracing.sample_rate = float(os.environ["SENTINELLOG_TRACE_SAMPLE_RATE"])
            except ValueError:
                pass

        return inst


_GLOBAL_CONFIG: Optional[ObservabilityConfig] = None


def get_observability_config() -> ObservabilityConfig:
    """Retrieve or initialize the global ObservabilityConfig instance."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = ObservabilityConfig.load()
    return _GLOBAL_CONFIG
