"""Release metadata and immutable version identification for SentinelLog deployments."""

import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

# Authoritative Phase 15 release version
APPLICATION_VERSION = "0.15.0"
FROZEN_PHASE12_HASH = "d3fdf5e83bbb24040416f11637ace5f181bb3db028b2aa61fe0e343ac20eaca3"


@dataclass(frozen=True)
class ReleaseMetadata:
    """Immutable release metadata identifying application build and provenance."""

    application_name: str
    version: str
    git_commit: str
    image_tag: str
    image_digest: str
    build_timestamp: str
    environment: str
    frozen_phase12_benchmark_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Return safe dictionary representation without leaking paths or secrets."""
        return asdict(self)


def get_release_metadata(environment: Optional[str] = None) -> ReleaseMetadata:
    """Extract release metadata from environment or deterministic defaults."""
    env_name = environment or os.getenv("SENTINELLOG_ENV", "development")
    git_commit = os.getenv("SENTINELLOG_GIT_COMMIT", "e8dfa6f")
    image_tag = os.getenv("SENTINELLOG_IMAGE_TAG", f"v{APPLICATION_VERSION}")
    image_digest = os.getenv(
        "SENTINELLOG_IMAGE_DIGEST",
        "sha256:7f9b8c1a2e3d4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
    )
    build_timestamp = os.getenv("SENTINELLOG_BUILD_TIMESTAMP", "2026-10-07T07:35:00Z")

    return ReleaseMetadata(
        application_name="SentinelLog",
        version=APPLICATION_VERSION,
        git_commit=git_commit,
        image_tag=image_tag,
        image_digest=image_digest,
        build_timestamp=build_timestamp,
        environment=env_name,
        frozen_phase12_benchmark_hash=FROZEN_PHASE12_HASH,
    )
