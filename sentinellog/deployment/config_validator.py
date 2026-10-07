"""Startup and pre-flight deployment configuration validation."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigurationValidationError(Exception):
    """Raised when environment or deployment configuration violates safety invariants."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass
class ValidationReport:
    """Report detailing outcome of deployment configuration checks."""

    valid: bool
    environment: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "environment": self.environment,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def load_env_config(environment: str, configs_root: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration YAML for given environment name."""
    root = Path(configs_root or "configs")
    target = root / environment / "app.yaml"
    if not target.exists():
        raise ConfigurationValidationError(f"Configuration file not found for environment '{environment}' at {target}")

    with open(target, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ConfigurationValidationError(f"Malformed configuration file at {target}: root must be a mapping")

    return data


def validate_deployment_config(
    config: Dict[str, Any],
    check_env_vars: bool = False,
) -> ValidationReport:
    """Validate deployment configuration against strict safety invariants.
    
    Args:
        config: Parsed configuration dictionary.
        check_env_vars: If True, asserts referenced *_env variables are present in os.environ.
        
    Returns:
        ValidationReport instance.
    """
    errors: List[str] = []
    warnings: List[str] = []

    env_name = config.get("environment", "")
    if env_name not in ("development", "staging", "production"):
        errors.append(f"Invalid environment '{env_name}'. Must be one of: development, staging, production.")
        return ValidationReport(valid=False, environment=env_name, errors=errors)

    server = config.get("server", {})
    security = config.get("security", {})
    ratelimit = config.get("ratelimit", {})
    storage = config.get("storage", {})
    database = config.get("database", {})
    vector_db = config.get("vector_db", {})

    # Invariants for staging and production
    is_hardened_env = env_name in ("staging", "production")

    if is_hardened_env:
        # Rule 24 / Rule 78: Debug mode forbidden in production & staging
        if server.get("debug") is True:
            errors.append(f"Debug mode is strictly forbidden in {env_name} environment.")

        # Rule 5 / Rule 76: Authentication must be enabled
        if security.get("auth_enabled") is not True:
            errors.append(f"Authentication must be enabled in {env_name} environment.")

        # Rule 10 / Rule 77: Wildcard CORS forbidden
        cors_origins = security.get("cors_allowed_origins", [])
        if not cors_origins:
            errors.append(f"CORS allowed origins must be explicitly declared in {env_name} environment.")
        elif "*" in cors_origins:
            errors.append(f"Wildcard CORS ('*') is strictly forbidden in {env_name} environment.")

        # Request limits
        max_bytes = security.get("max_request_bytes", 0)
        if max_bytes <= 0 or max_bytes > 10485760:  # 10 MB absolute max
            errors.append(f"Invalid max_request_bytes ({max_bytes}) in {env_name}. Must be positive and <= 10MB.")

        # Rate limiting must be enabled
        if ratelimit.get("enabled") is not True:
            errors.append(f"Rate limiting must be enabled in {env_name} environment.")

        # Distributed rate limiting backend in multi-replica production
        if env_name == "production" and ratelimit.get("backend") != "redis":
            warnings.append("Production environment specifies non-redis rate limiting; distributed scaling requires Redis.")

        # Database requirements
        if database.get("required") is True:
            if database.get("tls_required") is not True:
                errors.append(f"Database TLS must be required in {env_name} environment.")

        # Optional active runtime environment variable checks
        if check_env_vars:
            # Check API key variable
            key_var = security.get("api_key_env")
            if key_var and not os.getenv(key_var):
                errors.append(f"Required secret environment variable '{key_var}' is missing.")

            # Check database credentials
            if database.get("required"):
                for field in ("host_env", "user_env", "password_env"):
                    var = database.get(field)
                    if var and not os.getenv(var):
                        errors.append(f"Required database environment variable '{var}' is missing.")

            # Check vector db credentials
            if vector_db.get("required"):
                for field in ("url_env", "api_key_env"):
                    var = vector_db.get(field)
                    if var and not os.getenv(var):
                        errors.append(f"Required vector database environment variable '{var}' is missing.")

            # Check storage bucket
            if storage.get("backend") == "s3":
                bucket_var = storage.get("bucket_name_env")
                if bucket_var and not os.getenv(bucket_var):
                    errors.append(f"Required storage bucket environment variable '{bucket_var}' is missing.")

    return ValidationReport(
        valid=len(errors) == 0,
        environment=env_name,
        errors=errors,
        warnings=warnings,
    )


def validate_or_raise(config: Dict[str, Any], check_env_vars: bool = False) -> ValidationReport:
    """Validate configuration and raise ConfigurationValidationError if invalid."""
    report = validate_deployment_config(config, check_env_vars=check_env_vars)
    if not report.valid:
        error_msg = f"Deployment configuration validation failed for '{report.environment}': " + "; ".join(report.errors)
        raise ConfigurationValidationError(error_msg, errors=report.errors)
    return report
