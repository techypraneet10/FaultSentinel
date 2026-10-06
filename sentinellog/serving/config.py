"""Serving configuration models and environment variable overrides."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml

from sentinellog.serving.version import API_VERSION, SERVING_VERSION


class ServerSettings(BaseModel):
    """Network and runtime server settings."""

    host: str = "127.0.0.1"
    port: int = 8000
    environment: str = "production"
    log_level: str = "INFO"
    request_timeout: float = 30.0
    max_log_records: int = 500
    max_log_line_length: int = 4096
    max_request_bytes: int = 1048576  # 1 MB
    cors_origins: List[str] = Field(default_factory=list)
    api_version: str = API_VERSION


class PipelineSettings(BaseModel):
    """Pipeline and data path settings."""

    data_root: str = "data/processed"
    results_root: str = "results"
    phase7_results: str = "results/phase7"
    phase8_results: str = "results/phase8"
    phase9_results: str = "results/phase9"
    supported_datasets: List[str] = Field(default_factory=lambda: ["hdfs", "bgl"])


class ExplanationSettings(BaseModel):
    """LLM explanation orchestration settings."""

    provider: str = "mock"
    model_name: str = "mock-deterministic-v1"
    timeout_sec: float = 15.0


class ServingConfig(BaseModel):
    """Root configuration model for SentinelLog Serving Layer."""

    server: ServerSettings = Field(default_factory=ServerSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    explanation: ExplanationSettings = Field(default_factory=ExplanationSettings)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ServingConfig":
        """Load configuration from YAML file and apply environment variable overrides."""
        cfg_dict: Dict[str, Any] = {}
        target_path = config_path or os.getenv("SENTINELLOG_CONFIG_PATH", "configs/phase10.yaml")
        if target_path and Path(target_path).exists():
            with open(target_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    cfg_dict = loaded

        config = cls.model_validate(cfg_dict)
        config.apply_env_overrides()
        return config

    def apply_env_overrides(self) -> None:
        """Apply environment variables prefixed with SENTINELLOG_."""
        if "SENTINELLOG_HOST" in os.environ:
            self.server.host = os.environ["SENTINELLOG_HOST"]
        if "SENTINELLOG_PORT" in os.environ:
            try:
                self.server.port = int(os.environ["SENTINELLOG_PORT"])
            except ValueError:
                pass
        if "SENTINELLOG_ENV" in os.environ:
            self.server.environment = os.environ["SENTINELLOG_ENV"]
        if "SENTINELLOG_LOG_LEVEL" in os.environ:
            self.server.log_level = os.environ["SENTINELLOG_LOG_LEVEL"]
        if "SENTINELLOG_REQUEST_TIMEOUT" in os.environ:
            try:
                self.server.request_timeout = float(os.environ["SENTINELLOG_REQUEST_TIMEOUT"])
            except ValueError:
                pass
        if "SENTINELLOG_MAX_LOG_RECORDS" in os.environ:
            try:
                self.server.max_log_records = int(os.environ["SENTINELLOG_MAX_LOG_RECORDS"])
            except ValueError:
                pass
        if "SENTINELLOG_MAX_LOG_LINE_LENGTH" in os.environ:
            try:
                self.server.max_log_line_length = int(os.environ["SENTINELLOG_MAX_LOG_LINE_LENGTH"])
            except ValueError:
                pass
        if "SENTINELLOG_MAX_REQUEST_BYTES" in os.environ:
            try:
                self.server.max_request_bytes = int(os.environ["SENTINELLOG_MAX_REQUEST_BYTES"])
            except ValueError:
                pass
        if "SENTINELLOG_CORS_ORIGINS" in os.environ:
            raw = os.environ["SENTINELLOG_CORS_ORIGINS"].strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    self.server.cors_origins = json.loads(raw)
                except Exception:
                    self.server.cors_origins = [o.strip() for o in raw[1:-1].split(",") if o.strip()]
            else:
                self.server.cors_origins = [o.strip() for o in raw.split(",") if o.strip()]


_default_config: Optional[ServingConfig] = None


def get_default_config() -> ServingConfig:
    """Retrieve or initialize default serving configuration."""
    global _default_config
    if _default_config is None:
        _default_config = ServingConfig.load()
    return _default_config
