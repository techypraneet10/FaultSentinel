"""Phase 8 execution runner for Deterministic Incident Reasoning Engine.

Coordinates:
1. Loading Phase 6 evidence selections and Phase 7 verified citation bundles for HDFS and BGL.
2. Scoring escalated calibration windows with Phase 3 (B0) and Phase 4 (B2) models.
3. Executing IncidentReasoningEngine across all escalated windows.
4. Executing deterministic ablations (A, B, C, D).
5. Serializing auditable artifacts (assessments, traces, contributions, manifest, metrics).
6. Generating overall Phase 8 report.

Rule 1 (Test Set Protection) is strictly enforced: TEST is never loaded or accessed.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence
import torch
import yaml

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.artifacts import save_reasoning_artifacts
from sentinellog.reasoning.engine import (
    IncidentReasoningEngine,
    compute_configuration_hash,
)
from sentinellog.reasoning.schemas import (
    IncidentAssessment,
    ReasoningResult,
    ReasoningSummary,
)
from sentinellog.reasoning.validation import validate_reasoning_split
from sentinellog.reasoning.version import ENGINE_VERSION
from sentinellog.scoring.artifacts import (
    compute_sha256,
    get_git_commit_sha,
    guard_no_test_split,
)
from sentinellog.scoring.b0 import FrequencyScorer
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.b2_model import SequentialGRU
from sentinellog.scoring.baselines import load_windows


def load_b2_model(checkpoint_path: str, train_windows: List[LogWindow], seed: int = 42) -> B2SequentialScorer:
    """Load fitted Phase 4 B2 sequential scorer from disk."""
    b2 = B2SequentialScorer(random_state=seed)
    b2.tokenizer.fit(train_windows)
    ckpt = torch.load(checkpoint_path, weights_only=False)
    m_meta = ckpt.get("model_metadata", {})
    b2.model = SequentialGRU(
        vocab_size=b2.tokenizer.vocab_size,
        embedding_dim=m_meta.get("embedding_dim", b2.embedding_dim),
        hidden_dim=m_meta.get("hidden_dim", b2.hidden_dim),
        num_layers=m_meta.get("num_layers", b2.num_layers),
        dropout=0.0,
    )
    b2.model.load_state_dict(ckpt["model_state_dict"])
    b2.model.eval()
    b2.is_fitted = True
    return b2


def run_phase8_dataset(
    dataset: str,
    config: Dict[str, Any],
    phase6_dir: str = "results/phase6",
    phase7_dir: str = "results/phase7",
    phase4_dir: str = "results/phase4",
    data_root: str = "data/processed",
    output_dir: str = "results/phase8",
    source_commit: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete Phase 8 incident reasoning pipeline for a single dataset."""
    git_sha = source_commit or get_git_commit_sha()
    cfg_hash = compute_configuration_hash(config)
    seed = config.get("engine", {}).get("random_seed", 42)

    # Rule 1 & Split Protection Checks
    guard_no_test_split("calibration")
    validate_reasoning_split("calibration")

    print(f"[{dataset.upper()}] Loading Phase 7 citation bundles from {phase7_dir}/{dataset}...")
    p7_citations_file = os.path.join(phase7_dir, dataset, "citations.jsonl")
    p7_manifest_file = os.path.join(phase7_dir, dataset, "provenance_manifest.json")
    p6_selection_file = os.path.join(phase6_dir, dataset, "evidence_selection.jsonl")
    p6_manifest_file = os.path.join(phase6_dir, dataset, "reranking_manifest.json")

    if not os.path.exists(p7_citations_file):
        raise FileNotFoundError(f"Phase 7 citations file not found: {p7_citations_file}")

    with open(p7_manifest_file, "r", encoding="utf-8") as f:
        p7_manifest = json.load(f)
    with open(p6_manifest_file, "r", encoding="utf-8") as f:
        p6_manifest = json.load(f)

    phase6_commit = p6_manifest.get("source_commit", "c6097b7")
    phase7_commit = p7_manifest.get("phase7_commit", "b65ec6b")

    # Load CitationBundles
    bundles: List[CitationBundle] = []
    with open(p7_citations_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                bundles.append(CitationBundle.from_dict(json.loads(line)))

    bundle_map = {b.query_id: b for b in bundles}
    print(f"[{dataset.upper()}] Loaded {len(bundles)} Phase 7 citation bundles.")

    # Load Windows
    train_file = os.path.join(data_root, dataset, "train.jsonl")
    calib_file = os.path.join(data_root, dataset, "calibration.jsonl")

    train_windows = load_windows(train_file, "train")
    calib_windows = load_windows(calib_file, "calibration")
    calib_map = {w.window_id: w for w in calib_windows}

    # Match escalated windows
    escalated_windows = [calib_map[b.query_id] for b in bundles if b.query_id in calib_map]

    # Compute deterministic anomaly scores via B0 and B2 models
    print(f"[{dataset.upper()}] Scoring {len(escalated_windows)} escalated windows with B0 and B2 models...")
    b0_scorer = FrequencyScorer()
    b0_scorer.fit(train_windows)
    b0_scores = b0_scorer.score(escalated_windows)

    b2_ckpt_path = os.path.join(phase4_dir, dataset, "b2_model.pt")
    b2_scorer = load_b2_model(b2_ckpt_path, train_windows, seed=seed)
    b2_scores = b2_scorer.score(escalated_windows)

    # Initialize Reasoning Engine
    engine = IncidentReasoningEngine(config=config)

    # Primary Reasoning Execution
    results: List[ReasoningResult] = []
    start_time = time.perf_counter()

    for win, b2_s, b0_s in zip(escalated_windows, b2_scores, b0_scores):
        b = bundle_map.get(win.window_id)
        res = engine.assess(
            window=win,
            anomaly_score=float(b2_s),
            gate_decision="ESCALATE",
            citation_bundle=b,
            b0_score=float(b0_s),
            ablation_mode=None,
        )
        results.append(res)

    duration = time.perf_counter() - start_time

    # Diagnostic Metrics Aggregation
    decisions = [r.assessment.decision for r in results]
    severities = [r.assessment.severity for r in results]
    sufficiencies = [r.assessment.signal_summary.get("evidence_sufficiency") for r in results]
    prov_statuses = [r.assessment.provenance_status for r in results]
    conf_counts = [len(r.assessment.reasoning_trace.conflicts) for r in results]
    ev_counts = [len(r.assessment.evidence_contributions) for r in results]
    ev_rels = [
        float(r.assessment.signal_summary.get("evidence_relevance_mean", 0.0))
        for r in results
    ]
    confidences = [r.assessment.confidence for r in results]

    rule_frequencies: Dict[str, int] = Counter()
    for r in results:
        for rf in r.assessment.reasoning_trace.rules_fired:
            rule_frequencies[rf] += 1

    summary = ReasoningSummary(
        dataset=dataset,
        split="calibration",
        engine_version=ENGINE_VERSION,
        configuration_hash=cfg_hash,
        total_assessed=len(results),
        decision_distribution=dict(Counter(decisions)),
        severity_distribution=dict(Counter(severities)),
        sufficiency_distribution=dict(Counter(sufficiencies)),
        provenance_status_distribution=dict(Counter(prov_statuses)),
        conflict_count=sum(conf_counts),
        conflict_rate=round(float(sum(1 for c in conf_counts if c > 0) / max(len(results), 1)), 4),
        average_evidence_count=round(float(sum(ev_counts) / max(len(results), 1)), 4),
        average_evidence_relevance=round(float(sum(ev_rels) / max(len(results), 1)), 4),
        average_confidence=round(float(sum(confidences) / max(len(results), 1)), 4),
        rule_firing_frequencies=dict(rule_frequencies),
    )

    # 4 Deterministic Ablations (A, B, C, D)
    ablations_summary: Dict[str, Any] = {}
    for ab_mode in ["single_strongest_signal", "relevance_only", "conflict_ignored", "sufficiency_disabled"]:
        ab_results = []
        for win, b2_s, b0_s in zip(escalated_windows, b2_scores, b0_scores):
            b = bundle_map.get(win.window_id)
            r = engine.assess(
                window=win,
                anomaly_score=float(b2_s),
                gate_decision="ESCALATE",
                citation_bundle=b,
                b0_score=float(b0_s),
                ablation_mode=ab_mode,
            )
            ab_results.append(r)

        ab_decisions = dict(Counter([r.assessment.decision for r in ab_results]))
        ab_severities = dict(Counter([r.assessment.severity for r in ab_results]))
        ablations_summary[ab_mode] = {
            "decisions": ab_decisions,
            "severities": ab_severities,
            "avg_confidence": round(float(sum(r.assessment.confidence for r in ab_results) / len(ab_results)), 4),
        }

    # Record input hashes for traceability
    input_artifact_hashes = {
        p7_citations_file.replace("\\", "/"): compute_sha256(p7_citations_file),
        p6_selection_file.replace("\\", "/"): compute_sha256(p6_selection_file),
        train_file.replace("\\", "/"): compute_sha256(train_file),
        calib_file.replace("\\", "/"): compute_sha256(calib_file),
    }

    # Save artifacts
    artifact_hashes = save_reasoning_artifacts(
        dataset=dataset,
        output_dir=output_dir,
        results=results,
        summary=summary,
        config_hash=cfg_hash,
        source_commit=git_sha,
        input_artifact_hashes=input_artifact_hashes,
        phase6_commit=phase6_commit,
        phase7_commit=phase7_commit,
    )

    return {
        "dataset": dataset,
        "summary": summary.to_dict(),
        "ablations": ablations_summary,
        "artifact_hashes": artifact_hashes,
    }, duration


def main() -> None:
    """CLI entrypoint for Phase 8 execution."""
    parser = argparse.ArgumentParser(description="SentinelLog Phase 8: Deterministic Incident Reasoning Engine")
    parser.add_argument("--config", type=str, default="configs/phase8.yaml", help="Path to Phase 8 config")
    parser.add_argument("--datasets", nargs="+", default=["hdfs", "bgl"], help="Datasets to evaluate")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    paths = config.get("paths", {})
    phase6_dir = paths.get("phase6_dir", "results/phase6")
    phase7_dir = paths.get("phase7_dir", "results/phase7")
    output_dir = paths.get("output_dir", "results/phase8")
    data_root = paths.get("data_root", "data/processed")
    os.makedirs(output_dir, exist_ok=True)
    canonical_commit = config.get("source_commit") or "973da9d3367a8d9975790bd94e12e0d8b01f3b23"

    summary_report: Dict[str, Any] = {
        "phase": 8,
        "title": "SentinelLog Phase 8: Deterministic Incident Reasoning Engine",
        "source_commit": canonical_commit,
        "configuration_hash": compute_configuration_hash(config),
        "test_used": False,  # Rule 1 Invariant
        "datasets": {},
        "runtime_metadata": {
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "execution_timing_seconds": {},
        },
    }

    for dataset in args.datasets:
        diag, duration = run_phase8_dataset(
            dataset=dataset,
            config=config,
            phase6_dir=phase6_dir,
            phase7_dir=phase7_dir,
            phase4_dir="results/phase4",
            data_root=data_root,
            output_dir=output_dir,
            source_commit=canonical_commit,
        )
        summary_report["datasets"][dataset] = diag
        summary_report["runtime_metadata"]["execution_timing_seconds"][dataset] = round(duration, 6)

    # Write summary report JSON
    report_json_path = os.path.join(output_dir, "phase8_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, sort_keys=True)

    # Write summary report Markdown
    report_md_path = os.path.join(output_dir, "phase8_report.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 8 Summary Report: Deterministic Incident Reasoning Engine\n\n")
        f.write(f"- **Git Commit**: `{summary_report['source_commit']}`\n")
        f.write(f"- **Configuration Hash**: `{summary_report['configuration_hash']}`\n")
        f.write(f"- **Rule 1 Enforced (Test Used)**: `{summary_report['test_used']}`\n\n")

        for ds_name, ds_diag in summary_report["datasets"].items():
            summ = ds_diag["summary"]
            f.write(f"## Dataset: {ds_name.upper()}\n\n")
            f.write(f"- **Total Windows Assessed**: {summ['total_assessed']}\n")
            f.write(f"- **Decision Distribution**: `{summ['decision_distribution']}`\n")
            f.write(f"- **Severity Distribution**: `{summ['severity_distribution']}`\n")
            f.write(f"- **Sufficiency Distribution**: `{summ['sufficiency_distribution']}`\n")
            f.write(f"- **Provenance Status Distribution**: `{summ['provenance_status_distribution']}`\n")
            f.write(f"- **Conflict Rate**: {summ['conflict_rate'] * 100:.1f}%\n")
            f.write(f"- **Average Evidence Count**: {summ['average_evidence_count']:.2f}\n")
            f.write(f"- **Average Evidence Relevance**: {summ['average_evidence_relevance']:.4f}\n")
            f.write(f"- **Average Confidence (Support Strength)**: {summ['average_confidence']:.4f}\n")
            f.write(f"- **Rule Firing Frequencies**: `{summ['rule_firing_frequencies']}`\n\n")

            f.write("### Ablation Sensitivity Diagnostics\n\n")
            for ab_name, ab_info in ds_diag["ablations"].items():
                f.write(f"- **{ab_name}**: Decisions={ab_info['decisions']}, Severities={ab_info['severities']}, AvgConf={ab_info['avg_confidence']:.4f}\n")

            f.write("\n---\n\n")

        f.write("## Runtime Execution Metadata\n\n")
        f.write(f"- **Execution Timestamp**: {summary_report['runtime_metadata']['execution_timestamp']}\n")
        f.write(f"- **Python Version**: `{summary_report['runtime_metadata']['python_version']}`\n")
        timing_strs = [f"{k}={v:.4f}s" for k, v in summary_report['runtime_metadata']['execution_timing_seconds'].items()]
        f.write(f"- **Execution Timing**: {', '.join(timing_strs)}\n")
        f.write("- **Note**: Runtime metadata is strictly separated from deterministic content artifacts.\n\n")

    print(f"Phase 8 execution complete. Artifacts written to {output_dir}")


if __name__ == "__main__":
    main()
