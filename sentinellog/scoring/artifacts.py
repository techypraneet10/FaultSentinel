"""Artifact management, serialization, and test-protection guards for Phase 3.

Enforces Rule 1 (Test Set Protection) programmatically and handles reproducible
serialization of baseline models, experiment manifests, and calibration diagnostics.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, Optional
import joblib


class TestAccessViolationError(PermissionError):
    """Raised when an operation attempts to access the frozen test set in violation of Rule 1."""
    __test__ = False


def guard_no_test_split(split_name: str, file_path: Optional[str] = None) -> None:
    """Enforce Rule 1: Test set access is strictly forbidden during Phase 3.

    Args:
        split_name: Name of the partition (e.g., 'train', 'calibration', 'test').
        file_path: Optional file path being accessed.

    Raises:
        TestAccessViolationError: If split_name is 'test' or file_path points to test.jsonl.
    """
    clean_split = split_name.strip().lower()
    if clean_split == "test":
        raise TestAccessViolationError(
            "Rule 1 Violation: Access to 'test' split is strictly forbidden during Phase 3. "
            "The test split is reserved exclusively for Phase 7 frozen evaluation."
        )

    if file_path is not None:
        p = Path(file_path)
        # Check if the filename or immediate parts contain 'test.jsonl'
        if p.name.lower() == "test.jsonl" or "test" in [part.lower() for part in p.parts[-2:]]:
            raise TestAccessViolationError(
                f"Rule 1 Violation: Attempted to access test file '{file_path}' in Phase 3. "
                "All baseline fitting and threshold selection must use TRAIN and CALIBRATION only."
            )


def get_git_commit_sha() -> str:
    """Retrieve current Git commit SHA for experiment provenance."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "UNKNOWN_GIT_SHA"


def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def save_model_artifact(model: Any, out_path: str) -> None:
    """Save trained baseline model artifact using joblib."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(model, out_path)


def load_model_artifact(model_path: str) -> Any:
    """Load baseline model artifact from disk."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found: {model_path}")
    return joblib.load(model_path)


def save_experiment_manifest(manifest: Dict[str, Any], out_path: str) -> None:
    """Serialize experiment provenance manifest as formatted JSON."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def save_diagnostics(diagnostics: Dict[str, Any], out_path: str) -> None:
    """Serialize calibration diagnostics as formatted JSON."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)
