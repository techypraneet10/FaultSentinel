"""Artifact serialization, metrics computation, and manifest management for Phase 9.

Serializes:
- explanations.jsonl
- claims.jsonl
- validation.jsonl
- metrics.json
- manifest.json
- phase9_report.json
- phase9_report.md

Ensures:
- Rule 29 & 32: Runtime metadata separated from deterministic content hashes.
- Rule 40 & 41: Engineering diagnostics reported without fabricating human evaluation numbers.
- Rule 55: Engine and prompt versions tracked.
"""

from collections import Counter
import json
import os
from typing import Any, Dict, List, Optional, Sequence

from sentinellog.explanation.schemas import ExplanationResult
from sentinellog.explanation.version import EXPLANATION_ENGINE_VERSION, PROMPT_VERSION
from sentinellog.scoring.artifacts import compute_sha256, get_git_commit_sha


def save_explanation_artifacts(
    dataset: str,
    output_dir: str,
    results: Sequence[ExplanationResult],
    config_hash: str,
    source_commit: Optional[str] = None,
    phase8_commit: Optional[str] = None,
    input_artifact_hashes: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Serialize all Phase 9 artifacts for a single dataset.
    
    Args:
        dataset: Dataset identifier ('hdfs' or 'bgl').
        output_dir: Root destination directory (e.g. 'results/phase9').
        results: Sequence of ExplanationResult records.
        config_hash: SHA-256 of canonical configuration.
        source_commit: Current Git commit SHA.
        phase8_commit: Phase 8 commit SHA.
        input_artifact_hashes: Dictionary of input file hashes.
        
    Returns:
        Dictionary mapping artifact filenames to their SHA-256 digests.
    """
    ds_dir = os.path.join(output_dir, dataset.strip().lower())
    os.makedirs(ds_dir, exist_ok=True)
    git_sha = source_commit or get_git_commit_sha()

    # 1. explanations.jsonl (Deterministic serialization without volatile runtime fields)
    explanations_path = os.path.join(ds_dir, "explanations.jsonl")
    with open(explanations_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict(include_runtime=False), sort_keys=True) + "\n")

    # 2. claims.jsonl
    claims_path = os.path.join(ds_dir, "claims.jsonl")
    with open(claims_path, "w", encoding="utf-8") as f:
        for r in results:
            for c in r.claims:
                record = {
                    "window_id": r.window_id,
                    "dataset": r.dataset,
                    "split": r.split,
                    "claim": c.to_dict(),
                }
                f.write(json.dumps(record, sort_keys=True) + "\n")

    # 3. validation.jsonl
    validation_path = os.path.join(ds_dir, "validation.jsonl")
    with open(validation_path, "w", encoding="utf-8") as f:
        for r in results:
            record = {
                "window_id": r.window_id,
                "dataset": r.dataset,
                "split": r.split,
                "explanation_status": r.explanation_status,
                "abstained": r.abstained,
                "abstention_reason": r.abstention_reason,
                "citation_validation_status": r.citation_validation_status,
                "faithfulness_status": r.faithfulness_status,
                "validation_trace": r.validation_trace,
            }
            f.write(json.dumps(record, sort_keys=True) + "\n")

    # 4. Metrics Aggregation (Rule 40)
    total_attempted = len(results)
    successful = sum(1 for r in results if r.explanation_status == "GENERATED")
    abstained = sum(1 for r in results if r.abstained)
    provider_errors = sum(1 for r in results if r.explanation_status == "PROVIDER_ERROR")
    validation_failures = sum(1 for r in results if r.explanation_status == "VALIDATION_FAILED")
    decision_failures = sum(
        1 for r in results
        if any(t.get("step") == "decision_immutability" and not t.get("passed", False) for t in r.validation_trace)
    )

    all_claims = [c for r in results for c in r.claims]
    factual_claims = [c for c in all_claims if c.is_factual]
    supported_factual = sum(1 for c in factual_claims if c.supported)

    citation_coverage = (
        round(float(supported_factual / len(factual_claims)), 4)
        if factual_claims
        else 1.0
    )

    all_citations = [cit for r in results for cit in r.citations]
    all_cited_refs = [cid for c in all_claims for cid in c.citation_ids]
    valid_cited_refs = sum(
        1 for c in all_claims
        for cid in c.citation_ids
        if any(cit.citation_id == cid for cit in all_citations)
    )
    citation_precision = (
        round(float(valid_cited_refs / len(all_cited_refs)), 4)
        if all_cited_refs
        else 1.0
    )

    faith_distribution = dict(Counter(r.faithfulness_status for r in results))

    # Telemetry metrics (Rule 29)
    latencies = [r.usage_metadata.latency_ms for r in results if r.usage_metadata]
    in_tokens = sum(r.usage_metadata.input_tokens for r in results if r.usage_metadata)
    out_tokens = sum(r.usage_metadata.output_tokens for r in results if r.usage_metadata)
    tot_tokens = in_tokens + out_tokens
    retries = sum(r.usage_metadata.retry_count for r in results if r.usage_metadata)

    metrics = {
        "dataset": dataset,
        "split": results[0].split if results else "calibration",
        "explanation_engine_version": EXPLANATION_ENGINE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "total_attempted": total_attempted,
        "successful_generations": successful,
        "abstentions": abstained,
        "provider_failures": provider_errors,
        "validation_failures": validation_failures,
        "decision_consistency_failures": decision_failures,
        "total_claims": len(all_claims),
        "factual_claims": len(factual_claims),
        "supported_factual_claims": supported_factual,
        "citation_coverage": citation_coverage,
        "citation_precision": citation_precision,
        "unsupported_claim_rate": round(1.0 - citation_coverage, 4),
        "faithfulness_distribution": faith_distribution,
        "mean_latency_ms": round(float(sum(latencies) / max(len(latencies), 1)), 2),
        "total_input_tokens": in_tokens,
        "total_output_tokens": out_tokens,
        "total_tokens": tot_tokens,
        "total_retries": retries,
        "human_evaluation": "NOT_AVAILABLE",  # Rule 41: DO NOT fabricate human evaluation numbers
    }

    metrics_path = os.path.join(ds_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)

    # 5. Manifest
    artifact_hashes = {
        "explanations.jsonl": compute_sha256(explanations_path),
        "claims.jsonl": compute_sha256(claims_path),
        "validation.jsonl": compute_sha256(validation_path),
        "metrics.json": compute_sha256(metrics_path),
    }

    manifest = {
        "dataset": dataset,
        "split": metrics["split"],
        "explanation_engine_version": EXPLANATION_ENGINE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "configuration_hash": config_hash,
        "git_commit": git_sha,
        "phase8_commit": phase8_commit,
        "total_windows_assessed": total_attempted,
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
