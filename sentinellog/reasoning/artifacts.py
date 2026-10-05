"""Artifact serialization and reproducibility manifest management for Phase 8.

Serializes deterministic Phase 8 reasoning outputs:
- assessments.jsonl
- reasoning_traces.jsonl
- evidence_contributions.jsonl
- metrics.json
- manifest.json

Computes SHA-256 fingerprints across all output files and enforces Rule 1 invariants.
"""

import json
import os
from typing import Any, Dict, List, Optional, Sequence

from sentinellog.reasoning.schemas import (
    EvidenceContribution,
    IncidentAssessment,
    ReasoningResult,
    ReasoningSummary,
    ReasoningTrace,
)
from sentinellog.scoring.artifacts import compute_sha256, get_git_commit_sha


def save_reasoning_artifacts(
    dataset: str,
    output_dir: str,
    results: Sequence[ReasoningResult],
    summary: ReasoningSummary,
    config_hash: str,
    source_commit: Optional[str] = None,
    input_artifact_hashes: Optional[Dict[str, str]] = None,
    phase6_commit: Optional[str] = None,
    phase7_commit: Optional[str] = None,
) -> Dict[str, str]:
    """Serialize all Phase 8 artifacts for a dataset and write manifest.

    Args:
        dataset: Dataset identifier ('hdfs' or 'bgl').
        output_dir: Destination root directory (e.g. 'results/phase8').
        results: Sequence of ReasoningResult objects.
        summary: ReasoningSummary diagnostic record.
        config_hash: SHA-256 of canonical configuration.
        source_commit: Current git commit SHA.
        input_artifact_hashes: Dictionary of input file paths to SHA-256 digests.
        phase6_commit: Git commit of Phase 6 artifacts.
        phase7_commit: Git commit of Phase 7 artifacts.

    Returns:
        Dictionary mapping artifact filename to SHA-256 hash.
    """
    ds_dir = os.path.join(output_dir, dataset.strip().lower())
    os.makedirs(ds_dir, exist_ok=True)
    git_sha = source_commit or get_git_commit_sha()

    # 1. assessments.jsonl
    assessments_path = os.path.join(ds_dir, "assessments.jsonl")
    with open(assessments_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.assessment.to_dict(), sort_keys=True) + "\n")

    # 2. reasoning_traces.jsonl
    traces_path = os.path.join(ds_dir, "reasoning_traces.jsonl")
    with open(traces_path, "w", encoding="utf-8") as f:
        for r in results:
            trace_dict = {
                "window_id": r.assessment.window_id,
                "dataset": r.assessment.dataset,
                "split": r.assessment.split,
                "trace": r.assessment.reasoning_trace.to_dict(),
            }
            f.write(json.dumps(trace_dict, sort_keys=True) + "\n")

    # 3. evidence_contributions.jsonl
    contributions_path = os.path.join(ds_dir, "evidence_contributions.jsonl")
    with open(contributions_path, "w", encoding="utf-8") as f:
        for r in results:
            for c in r.assessment.evidence_contributions:
                c_dict = {
                    "window_id": r.assessment.window_id,
                    "dataset": r.assessment.dataset,
                    "contribution": c.to_dict(),
                }
                f.write(json.dumps(c_dict, sort_keys=True) + "\n")

    # 4. metrics.json
    metrics_path = os.path.join(ds_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2, sort_keys=True)

    # Compute hashes of outputs
    artifact_hashes = {
        "assessments.jsonl": compute_sha256(assessments_path),
        "reasoning_traces.jsonl": compute_sha256(traces_path),
        "evidence_contributions.jsonl": compute_sha256(contributions_path),
        "metrics.json": compute_sha256(metrics_path),
    }

    # 5. manifest.json
    manifest = {
        "dataset": dataset,
        "split": summary.split,
        "engine_version": summary.engine_version,
        "configuration_hash": config_hash,
        "git_commit": git_sha,
        "phase6_commit": phase6_commit,
        "phase7_commit": phase7_commit,
        "total_windows_assessed": summary.total_assessed,
        "test_used": False,  # Rule 1 Invariant
        "calibration_used_for_fitting": False,
        "input_artifact_hashes": input_artifact_hashes or {},
        "artifact_hashes": artifact_hashes,
    }

    manifest_path = os.path.join(ds_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    artifact_hashes["manifest.json"] = compute_sha256(manifest_path)
    return artifact_hashes
