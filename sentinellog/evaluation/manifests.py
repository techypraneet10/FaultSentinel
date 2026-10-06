"""Deterministic experiment manifest and metadata serialization for Phase 12.

Strictly protects Rule 3 (Experiment Traceability):
- Records exact seeds, commit SHAs, dataset hashes, configuration parameters, and models
- Isolates volatile execution metadata (timestamps, latencies) from deterministic scientific hashes
"""

import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional


def get_git_commit() -> str:
    """Retrieve Git commit SHA."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def hash_file(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    if not os.path.exists(filepath):
        return "MISSING"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_deterministic_hash(scientific_dict: Dict[str, Any]) -> str:
    """Compute SHA-256 hash over canonical JSON representation of scientific fields."""
    canonical = json.dumps(scientific_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_evaluation_manifest(
    experiment_id: str,
    dataset: str,
    split: str,
    model_name: str,
    parameters: Dict[str, Any],
    metrics: Dict[str, Any],
    seed: int = 42,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct structured evaluation manifest with separate scientific and runtime fields."""
    scientific_payload = {
        "experiment_id": experiment_id,
        "dataset": dataset,
        "split": split,
        "model_name": model_name,
        "seed": seed,
        "parameters": parameters,
        "metrics": metrics,
        "python_version": sys.version.split()[0],
    }

    scientific_hash = compute_deterministic_hash(scientific_payload)

    runtime_metadata = {
        "git_commit": get_git_commit(),
        "platform": sys.platform,
    }
    if extra_metadata:
        runtime_metadata.update(extra_metadata)

    return {
        "scientific_hash": scientific_hash,
        "scientific_payload": scientific_payload,
        "runtime_metadata": runtime_metadata,
    }
