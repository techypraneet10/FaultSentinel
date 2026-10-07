"""Comprehensive Phase 15 Test Suite: Deployment Architecture & Release Orchestration.

Covers:
1. Environment configuration loading and strict fail-closed validation.
2. Staging vs Production isolation (no shared resources or data).
3. Release metadata, semantic versioning, and immutable image digests.
4. Distributed rate limiting abstraction (memory backend and Redis fallback).
5. Terraform infrastructure definitions, security groups, and IAM roles.
6. ECS Fargate task hardening (non-root USER 10001, rolling deployment, healthchecks).
7. ALB target group readiness gating and HTTP-to-HTTPS redirection.
8. Storage security (S3 public access block, versioning, KMS encryption).
9. Automated rollback planning and deterministic smoke testing.
10. CI/CD workflow pipeline stages and promotion gates.
"""

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sentinellog.deployment.config_validator import (
    ConfigurationValidationError,
    ValidationReport,
    load_env_config,
    validate_deployment_config,
    validate_or_raise,
)
from sentinellog.deployment.metadata import (
    APPLICATION_VERSION,
    FROZEN_PHASE12_HASH,
    ReleaseMetadata,
    get_release_metadata,
)
from sentinellog.deployment.ratelimit import DistributedRateLimiter
from sentinellog.serving.app import create_app
from sentinellog.serving.config import ServingConfig
from deploy.smoke.smoke_test import run_smoke_tests
from deploy.scripts.rollback import execute_rollback


# ==============================================================================
# 1. Environment Configurations & Fail-Closed Validation
# ==============================================================================


class TestEnvironmentConfigurations:
    """Verifies environment YAML loading, staging/production isolation, and invariants."""

    def test_development_config_loads_and_validates(self):
        cfg = load_env_config("development")
        report = validate_deployment_config(cfg)
        assert report.valid is True
        assert report.environment == "development"
        assert cfg["server"]["debug"] is True
        assert cfg["security"]["auth_enabled"] is False

    def test_staging_config_loads_and_validates(self):
        cfg = load_env_config("staging")
        report = validate_deployment_config(cfg)
        assert report.valid is True
        assert report.environment == "staging"
        assert cfg["server"]["debug"] is False
        assert cfg["security"]["auth_enabled"] is True
        assert cfg["security"]["enforce_production_mode"] is True

    def test_production_config_loads_and_validates(self):
        cfg = load_env_config("production")
        report = validate_deployment_config(cfg)
        assert report.valid is True
        assert report.environment == "production"
        assert cfg["server"]["debug"] is False
        assert cfg["security"]["auth_enabled"] is True
        assert cfg["security"]["enforce_production_mode"] is True

    def test_staging_and_production_isolation_no_shared_resources(self):
        staging_cfg = load_env_config("staging")
        prod_cfg = load_env_config("production")

        # Staging and production must use distinct database names
        assert staging_cfg["database"]["name"] != prod_cfg["database"]["name"]
        # Must use distinct vector database collections
        assert staging_cfg["vector_db"]["collection"] != prod_cfg["vector_db"]["collection"]
        # Must use distinct bucket environment variables
        assert staging_cfg["storage"]["bucket_name_env"] != prod_cfg["storage"]["bucket_name_env"]
        # Must use distinct database host variables
        assert staging_cfg["database"]["host_env"] != prod_cfg["database"]["host_env"]

    def test_invalid_environment_name_rejected(self):
        bad_cfg = {"environment": "sandbox_unsupported"}
        report = validate_deployment_config(bad_cfg)
        assert report.valid is False
        assert "Invalid environment" in report.errors[0]

    def test_production_debug_mode_true_rejected(self):
        cfg = load_env_config("production")
        cfg["server"]["debug"] = True
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("Debug mode is strictly forbidden" in err for err in report.errors)

    def test_production_auth_disabled_rejected(self):
        cfg = load_env_config("production")
        cfg["security"]["auth_enabled"] = False
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("Authentication must be enabled" in err for err in report.errors)

    def test_production_wildcard_cors_rejected(self):
        cfg = load_env_config("production")
        cfg["security"]["cors_allowed_origins"] = ["*"]
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("Wildcard CORS" in err for err in report.errors)

    def test_production_missing_cors_origins_rejected(self):
        cfg = load_env_config("production")
        cfg["security"]["cors_allowed_origins"] = []
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("CORS allowed origins must be explicitly declared" in err for err in report.errors)

    def test_production_invalid_request_bytes_rejected(self):
        cfg = load_env_config("production")
        cfg["security"]["max_request_bytes"] = -100
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("Invalid max_request_bytes" in err for err in report.errors)

    def test_production_database_tls_enforced(self):
        cfg = load_env_config("production")
        cfg["database"]["tls_required"] = False
        report = validate_deployment_config(cfg)
        assert report.valid is False
        assert any("Database TLS must be required" in err for err in report.errors)

    def test_validate_or_raise_raises_on_invalid_config(self):
        cfg = load_env_config("production")
        cfg["server"]["debug"] = True
        with pytest.raises(ConfigurationValidationError, match="Debug mode is strictly forbidden"):
            validate_or_raise(cfg)

    def test_check_env_vars_fails_when_required_secrets_absent(self, monkeypatch):
        monkeypatch.delenv("SENTINELLOG_API_KEY", raising=False)
        cfg = load_env_config("production")
        report = validate_deployment_config(cfg, check_env_vars=True)
        assert report.valid is False
        assert any("SENTINELLOG_API_KEY" in err for err in report.errors)


# ==============================================================================
# 2. Release Metadata & Semantic Versioning
# ==============================================================================


class TestReleaseMetadataAndManifests:
    """Verifies immutable release identification, digests, and benchmark hash preservation."""

    def test_application_version_is_semantic(self):
        semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        assert semver_pattern.match(APPLICATION_VERSION), f"Version '{APPLICATION_VERSION}' must follow SemVer"

    def test_release_metadata_properties(self):
        meta = get_release_metadata("staging")
        assert meta.application_name == "SentinelLog"
        assert meta.version == APPLICATION_VERSION
        assert meta.environment == "staging"
        assert meta.git_commit is not None
        assert meta.image_tag.startswith("v")
        assert meta.image_digest.startswith("sha256:")

    def test_release_metadata_to_dict_contains_no_secrets(self):
        meta = get_release_metadata("production")
        d = meta.to_dict()
        assert "api_key" not in d
        assert "password" not in d
        assert "token" not in d
        assert "secret" not in d

    def test_release_metadata_preserves_frozen_phase12_hash(self):
        meta = get_release_metadata("production")
        assert meta.frozen_phase12_benchmark_hash == FROZEN_PHASE12_HASH

    def test_image_tag_not_latest(self):
        meta = get_release_metadata("production")
        assert meta.image_tag != "latest", "Production release image must never be tagged as 'latest'"

    def test_image_digest_is_valid_sha256(self):
        meta = get_release_metadata("production")
        digest_pattern = re.compile(r"^sha256:[a-f0-9]{64}$")
        assert digest_pattern.match(meta.image_digest)


# ==============================================================================
# 3. Distributed Rate Limiting
# ==============================================================================


class TestDistributedRateLimiting:
    """Verifies rate limiting abstraction with in-memory execution and Redis fallback."""

    def test_in_memory_backend_rate_limiting_allowed(self):
        limiter = DistributedRateLimiter(backend="memory", max_requests=5, window_seconds=10)
        for _ in range(5):
            allowed, retry = limiter.check_rate_limit("client-a")
            assert allowed is True
            assert retry == 0

    def test_in_memory_backend_rate_limit_exceeded_with_retry_after(self):
        limiter = DistributedRateLimiter(backend="memory", max_requests=2, window_seconds=10)
        assert limiter.check_rate_limit("client-b")[0] is True
        assert limiter.check_rate_limit("client-b")[0] is True
        allowed, retry = limiter.check_rate_limit("client-b")
        assert allowed is False
        assert 1 <= retry <= 10

    def test_redis_backend_fallback_when_redis_unavailable(self):
        # Configure redis backend with unreachable URL
        limiter = DistributedRateLimiter(
            backend="redis",
            max_requests=3,
            window_seconds=10,
            redis_url="redis://nonexistent-host:6379/0",
        )
        # Should gracefully fall back to local bounded in-memory limiter without crashing
        assert limiter.check_rate_limit("client-fallback")[0] is True
        assert limiter.check_rate_limit("client-fallback")[0] is True

    def test_redis_backend_mock_sliding_window_behavior(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        # Mock pipeline results: [removed_count, current_count, [(b'123.0', 123.0)]]
        mock_pipe.execute.return_value = [0, 10, [(b"ts", 1000.0)]]
        mock_redis.pipeline.return_value = mock_pipe

        limiter = DistributedRateLimiter(
            backend="redis",
            max_requests=5,
            window_seconds=60,
            redis_client=mock_redis,
        )
        # 10 is >= 5, should be rejected
        allowed, retry = limiter.check_rate_limit("client-redis")
        assert allowed is False
        assert retry > 0

    def test_distributed_rate_limiter_reset(self):
        limiter = DistributedRateLimiter(backend="memory", max_requests=2, window_seconds=10)
        limiter.check_rate_limit("client-c")
        limiter.check_rate_limit("client-c")
        assert limiter.check_rate_limit("client-c")[0] is False

        limiter.reset()
        assert limiter.check_rate_limit("client-c")[0] is True


# ==============================================================================
# 4. Terraform Infrastructure Definitions
# ==============================================================================


class TestInfrastructureDefinitions:
    """Verifies Terraform syntax, module presence, and security invariants."""

    def test_terraform_files_exist(self):
        infra_dir = Path("infra")
        assert infra_dir.exists()
        assert (infra_dir / "environments" / "staging" / "main.tf").exists()
        assert (infra_dir / "environments" / "production" / "main.tf").exists()

    def test_terraform_modules_present(self):
        modules_dir = Path("infra/modules")
        expected_modules = ["networking", "alb", "ecs", "ecr", "database", "storage", "secrets"]
        for mod in expected_modules:
            assert (modules_dir / mod / "main.tf").exists(), f"Module {mod} main.tf missing"
            assert (modules_dir / mod / "variables.tf").exists(), f"Module {mod} variables.tf missing"
            assert (modules_dir / mod / "outputs.tf").exists(), f"Module {mod} outputs.tf missing"

    def test_ecs_fargate_task_definition_uses_non_root_user(self):
        ecs_tf = Path("infra/modules/ecs/main.tf").read_text(encoding="utf-8")
        assert 'user      = "10001:10001"' in ecs_tf, "ECS Task definition must enforce unprivileged user 10001"

    def test_ecs_fargate_task_definition_defines_healthcheck(self):
        ecs_tf = Path("infra/modules/ecs/main.tf").read_text(encoding="utf-8")
        assert "healthCheck" in ecs_tf
        assert "/health/live" in ecs_tf

    def test_ecs_fargate_rolling_deployment_percentages(self):
        ecs_tf = Path("infra/modules/ecs/main.tf").read_text(encoding="utf-8")
        assert "deployment_minimum_healthy_percent = 100" in ecs_tf
        assert "deployment_maximum_percent         = 200" in ecs_tf

    def test_alb_target_group_uses_readiness_probe(self):
        alb_tf = Path("infra/modules/alb/main.tf").read_text(encoding="utf-8")
        assert 'path                = "/health/ready"' in alb_tf, "ALB target group must route traffic via /health/ready"

    def test_alb_http_redirects_to_https(self):
        alb_tf = Path("infra/modules/alb/main.tf").read_text(encoding="utf-8")
        assert 'protocol    = "HTTPS"' in alb_tf
        assert 'status_code = "HTTP_301"' in alb_tf

    def test_database_security_group_private_access_only(self):
        db_tf = Path("infra/modules/database/main.tf").read_text(encoding="utf-8")
        assert "security_groups = [var.ecs_security_group_id]" in db_tf
        assert "publicly_accessible = false" in db_tf

    def test_s3_storage_public_access_blocked_and_versioned(self):
        storage_tf = Path("infra/modules/storage/main.tf").read_text(encoding="utf-8")
        assert "block_public_acls       = true" in storage_tf
        assert "block_public_policy     = true" in storage_tf
        assert 'status = "Enabled"' in storage_tf  # Versioning

    def test_ecr_repository_immutable_tags(self):
        ecr_tf = Path("infra/modules/ecr/main.tf").read_text(encoding="utf-8")
        assert 'image_tag_mutability = "IMMUTABLE"' in ecr_tf
        assert "scan_on_push = true" in ecr_tf


# ==============================================================================
# 5. Rollback & Smoke Testing
# ==============================================================================


class TestRollbackAndSmokeTesting:
    """Verifies rollback generation and deterministic smoke testing against serving app."""

    def test_rollback_plan_generation(self):
        plan = execute_rollback(
            target_environment="production",
            target_image_tag="v0.14.0",
            target_digest="sha256:7f9b8c1a2e3d4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
            reason="Unstable task readiness post-deploy",
            dry_run=True,
        )
        assert plan["action"] == "ROLLBACK"
        assert plan["target_image_tag"] == "v0.14.0"
        assert len(plan["steps"]) >= 5
        assert plan["status"] == "PLAN_GENERATED"

    def test_smoke_test_execution_against_fastapi_app(self):
        app = create_app()
        client = TestClient(app)

        # Execute tests simulating smoke test checks
        res_live = client.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "ok"

        res_ready = client.get("/health/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "ready"

        res_ana = client.post(
            "/api/v1/analyze",
            json={"dataset": "hdfs", "logs": ["Block blk_1 added"]},
        )
        assert res_ana.status_code == 200
        assert "decision" in res_ana.json()
        assert "request_id" in res_ana.json()


# ==============================================================================
# 6. Container Hardening & CI/CD Pipelines
# ==============================================================================


class TestContainerAndCICDPipelines:
    """Verifies Dockerfile parameters, CI stages, and gitignore protection."""

    def test_dockerfile_uses_unprivileged_user(self):
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        assert "USER 10001:10001" in dockerfile
        assert "useradd -u 10001" in dockerfile

    def test_ci_workflow_defines_all_stages(self):
        ci_yaml = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "1. Checkout" in ci_yaml
        assert "2. Install Python" in ci_yaml
        assert "3. Run Backend Test Suite" in ci_yaml
        assert "4. Run Frontend Test Suite" in ci_yaml
        assert "5. Run Frontend Typecheck" in ci_yaml
        assert "6. Run Frontend Lint" in ci_yaml
        assert "7. Verify Python Bytecode" in ci_yaml
        assert "8. Execute Security Test Suite" in ci_yaml
        assert "9. Deterministic Repository Secret Scan" in ci_yaml
        assert "10. Dependency Vulnerability Audit" in ci_yaml
        assert "11. Build Docker" in ci_yaml
        assert "12. Container Security" in ci_yaml
        assert "13. Validate Release Manifests" in ci_yaml

    def test_release_workflow_defines_staging_and_production_gates(self):
        rel_yaml = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
        assert "environment: staging" in rel_yaml
        assert "environment:" in rel_yaml
        assert "name: production" in rel_yaml

    def test_gitignore_ignores_terraform_state_and_secrets(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")
        assert "*.tfstate" in gitignore
        assert ".terraform/" in gitignore
