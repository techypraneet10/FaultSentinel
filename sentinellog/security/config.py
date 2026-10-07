"""Security configuration models and validation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml
from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Centralized security configuration model for SentinelLog."""

    auth_enabled: bool = False
    api_key: Optional[str] = None
    analyst_api_key: Optional[str] = None
    operator_api_key: Optional[str] = None
    cors_allowed_origins: List[str] = Field(default_factory=list)
    max_request_bytes: int = 1048576  # 1 MB
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    trusted_proxies: List[str] = Field(default_factory=lambda: ["127.0.0.1", "::1"])
    debug: bool = False
    enforce_production_mode: bool = False

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "SecurityConfig":
        """Load configuration from YAML and apply SENTINELLOG_ environment overrides."""
        cfg_dict: Dict[str, Any] = {}
        target_path = config_path or os.getenv("SENTINELLOG_SECURITY_CONFIG_PATH", "configs/security.example.yaml")
        p = Path(target_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    cfg_dict = loaded.get("security", loaded)

        inst = cls(**cfg_dict)
        inst.apply_env_overrides()
        inst.validate_security_invariants()
        return inst

    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides prefixed with SENTINELLOG_."""
        if "SENTINELLOG_AUTH_ENABLED" in os.environ:
            self.auth_enabled = os.environ["SENTINELLOG_AUTH_ENABLED"].strip().lower() in ("true", "1", "yes")
        if "SENTINELLOG_API_KEY" in os.environ:
            self.api_key = os.environ["SENTINELLOG_API_KEY"].strip()
        if "SENTINELLOG_ANALYST_API_KEY" in os.environ:
            self.analyst_api_key = os.environ["SENTINELLOG_ANALYST_API_KEY"].strip()
        if "SENTINELLOG_OPERATOR_API_KEY" in os.environ:
            self.operator_api_key = os.environ["SENTINELLOG_OPERATOR_API_KEY"].strip()
        if "SENTINELLOG_CORS_ALLOWED_ORIGINS" in os.environ:
            raw = os.environ["SENTINELLOG_CORS_ALLOWED_ORIGINS"].strip()
            if raw.startswith("[") and raw.endswith("]"):
                import json
                try:
                    self.cors_allowed_origins = json.loads(raw)
                except Exception:
                    self.cors_allowed_origins = [o.strip() for o in raw[1:-1].split(",") if o.strip()]
            else:
                self.cors_allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]
        if "SENTINELLOG_MAX_REQUEST_BYTES" in os.environ:
            try:
                self.max_request_bytes = int(os.environ["SENTINELLOG_MAX_REQUEST_BYTES"])
            except ValueError:
                pass
        if "SENTINELLOG_RATE_LIMIT_ENABLED" in os.environ:
            self.rate_limit_enabled = os.environ["SENTINELLOG_RATE_LIMIT_ENABLED"].strip().lower() in ("true", "1", "yes")
        if "SENTINELLOG_RATE_LIMIT_REQUESTS" in os.environ:
            try:
                self.rate_limit_requests = int(os.environ["SENTINELLOG_RATE_LIMIT_REQUESTS"])
            except ValueError:
                pass
        if "SENTINELLOG_RATE_LIMIT_WINDOW_SECONDS" in os.environ:
            try:
                self.rate_limit_window_seconds = int(os.environ["SENTINELLOG_RATE_LIMIT_WINDOW_SECONDS"])
            except ValueError:
                pass
        if "SENTINELLOG_TRUSTED_PROXIES" in os.environ:
            raw = os.environ["SENTINELLOG_TRUSTED_PROXIES"].strip()
            self.trusted_proxies = [p.strip() for p in raw.split(",") if p.strip()]
        if "SENTINELLOG_DEBUG" in os.environ:
            self.debug = os.environ["SENTINELLOG_DEBUG"].strip().lower() in ("true", "1", "yes")
        if "SENTINELLOG_ENFORCE_PRODUCTION_MODE" in os.environ:
            self.enforce_production_mode = os.environ["SENTINELLOG_ENFORCE_PRODUCTION_MODE"].strip().lower() in ("true", "1", "yes")

    def validate_security_invariants(self) -> None:
        """Fail-closed startup checks against insecure configurations."""
        # Rule 76: If auth is enabled, API key must be non-empty
        if self.auth_enabled and (not self.api_key or len(self.api_key.strip()) < 8):
            raise ValueError(
                "Security configuration failure: SENTINELLOG_AUTH_ENABLED is true, but SENTINELLOG_API_KEY "
                "is missing, empty, or shorter than 8 characters. System fails closed."
            )

        # Rule 77: In hardened/production mode, wildcard CORS is forbidden
        if self.enforce_production_mode:
            if "*" in self.cors_allowed_origins:
                raise ValueError(
                    "Security configuration failure: Wildcard CORS ('*') is strictly forbidden in hardened production mode."
                )
            # Rule 78: In hardened/production mode, debug mode must be false
            if self.debug:
                raise ValueError(
                    "Security configuration failure: Debug mode cannot be enabled in hardened production mode."
                )


_GLOBAL_SECURITY_CONFIG: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Retrieve or initialize the global SecurityConfig instance."""
    global _GLOBAL_SECURITY_CONFIG
    if _GLOBAL_SECURITY_CONFIG is None:
        _GLOBAL_SECURITY_CONFIG = SecurityConfig.load()
    return _GLOBAL_SECURITY_CONFIG


def reset_security_config(config: Optional[SecurityConfig] = None) -> None:
    """Reset global security configuration (useful in testing)."""
    global _GLOBAL_SECURITY_CONFIG
    _GLOBAL_SECURITY_CONFIG = config
