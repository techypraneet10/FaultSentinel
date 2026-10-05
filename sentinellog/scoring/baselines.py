"""Baseline experiment execution engine and CLI runner for Phase 3.

Coordinates training and evaluation of unsupervised baselines:
- B0 (Frequency Scorer)
- B1 PCA (Reconstruction Error)
- B1 Isolation Forest (Anomaly Score)

Strictly adheres to Rule 1 (Test Set Protection) and Rule 7 (No Fabricated Results).
All models are fitted solely on TRAIN, calibrated on CALIBRATION, and TEST remains
strictly frozen and untouched.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import yaml

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.scoring.artifacts import (
    compute_sha256,
    get_git_commit_sha,
    guard_no_test_split,
    save_diagnostics,
    save_experiment_manifest,
    save_model_artifact,
)
from sentinellog.scoring.b0 import FrequencyScorer
from sentinellog.scoring.b1 import IsolationForestScorer, PCAScorer
from sentinellog.scoring.thresholds import (
    compute_unsupervised_threshold,
    evaluate_calibration_diagnostics,
)


def load_windows(file_path: str, split_name: str) -> List[LogWindow]:
    """Load windows from JSONL file with Rule 1 test-access guard.

    Args:
        file_path: Path to .jsonl file.
        split_name: Name of the split ('train' or 'calibration').

    Returns:
        List of LogWindow objects.
    """
    guard_no_test_split(split_name, file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Partition file not found: {file_path}")

    windows: List[LogWindow] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                windows.append(LogWindow.from_dict(json.loads(line)))

    return windows


def run_single_baseline(
    dataset: str,
    baseline_type: str,
    train_windows: List[LogWindow],
    calib_windows: List[LogWindow],
    config: Dict[str, Any],
    data_dir: str,
    out_dir: str,
) -> Dict[str, Any]:
    """Train baseline on TRAIN, evaluate diagnostics on CALIBRATION, and save artifacts."""
    git_sha = get_git_commit_sha()
    manifest_path = os.path.join(data_dir, "manifest.json")
    data_hash = compute_sha256(manifest_path) if os.path.exists(manifest_path) else "MISSING"

    start_time = time.perf_counter()

    # Instantiate baseline scorer
    if baseline_type == "b0":
        alpha = config.get("b0", {}).get("smoothing_alpha", 1.0)
        scorer = FrequencyScorer(alpha=alpha)
        baseline_name = "B0_Frequency"
    elif baseline_type == "b1_pca":
        mode = config.get("features", {}).get("mode", "normalized_count")
        pca_cfg = config.get("b1_pca", {})
        variance_ratio = pca_cfg.get("variance_ratio", 0.95)
        n_components = pca_cfg.get("n_components", None)
        seed = pca_cfg.get("random_state", config.get("random_seed", 42))
        scorer = PCAScorer(
            mode=mode,
            variance_ratio=variance_ratio,
            n_components=n_components,
            random_state=seed,
        )
        baseline_name = "B1_PCA"
    elif baseline_type == "b1_iforest":
        mode = config.get("features", {}).get("mode", "normalized_count")
        iforest_cfg = config.get("b1_iforest", {})
        n_estimators = iforest_cfg.get("n_estimators", 100)
        contamination = iforest_cfg.get("contamination", "auto")
        seed = iforest_cfg.get("random_state", config.get("random_seed", 42))
        scorer = IsolationForestScorer(
            mode=mode,
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=seed,
        )
        baseline_name = "B1_IsolationForest"
    else:
        raise ValueError(f"Unsupported baseline type: {baseline_type}")

    # 1. Fit strictly on TRAIN without anomaly labels
    scorer.fit(train_windows)
    train_fit_time = time.perf_counter() - start_time

    # 2. Score CALIBRATION windows
    score_start = time.perf_counter()
    calib_scores = scorer.score(calib_windows)
    scoring_time = time.perf_counter() - score_start

    # Also compute TRAIN scores for distribution diagnostics
    train_scores = scorer.score(train_windows)

    # 3. Derive unsupervised threshold from calibration scores
    quantile = float(config.get("threshold_quantile", 0.95))
    threshold = compute_unsupervised_threshold(calib_scores, quantile=quantile)

    # 4. Evaluate calibration diagnostics
    calib_labels = np.array([1 if w.is_anomaly else 0 for w in calib_windows], dtype=int)
    diagnostics = evaluate_calibration_diagnostics(
        scores=calib_scores,
        labels=calib_labels,
        threshold=threshold,
        windows=calib_windows,
        quantile=quantile,
    )

    # Add training distribution metadata to diagnostics
    train_labels = np.array([1 if w.is_anomaly else 0 for w in train_windows], dtype=int)
    diagnostics["train_score_distribution"] = {
        "min": float(np.min(train_scores)),
        "max": float(np.max(train_scores)),
        "mean": float(np.mean(train_scores)),
        "std": float(np.std(train_scores)),
        "p50": float(np.percentile(train_scores, 50)),
        "p95": float(np.percentile(train_scores, 95)),
    }
    diagnostics["timing"] = {
        "train_fit_seconds": train_fit_time,
        "calibration_scoring_seconds": scoring_time,
        "total_seconds": time.perf_counter() - start_time,
    }

    # 5. Build experiment manifest
    model_metadata = scorer.get_metadata()
    manifest = {
        "experiment": f"{dataset}_{baseline_type}",
        "dataset": dataset,
        "baseline": baseline_name,
        "seed": config.get("random_seed", 42),
        "data_manifest_hash": data_hash,
        "processing_version": config.get("version", "0.3.0-phase3"),
        "git_commit": git_sha,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_config": config.get("features", {}),
        "model_config": model_metadata,
        "threshold_config": {
            "strategy": "calibration_quantile",
            "quantile": quantile,
        },
        "threshold": threshold,
        "train_windows": len(train_windows),
        "calibration_windows": len(calib_windows),
        "test_used": False,  # RULE 1: Permanent invariant
    }

    # 6. Save experiment artifacts
    exp_out_dir = os.path.join(out_dir, dataset, baseline_type)
    os.makedirs(exp_out_dir, exist_ok=True)

    model_path = os.path.join(exp_out_dir, "model.joblib")
    manifest_path = os.path.join(exp_out_dir, "manifest.json")
    diagnostics_path = os.path.join(exp_out_dir, "diagnostics.json")

    save_model_artifact(scorer, model_path)
    save_experiment_manifest(manifest, manifest_path)
    save_diagnostics(diagnostics, diagnostics_path)

    return {
        "dataset": dataset,
        "baseline": baseline_name,
        "baseline_type": baseline_type,
        "threshold": threshold,
        "threshold_quantile": quantile,
        "model_path": model_path,
        "manifest_path": manifest_path,
        "diagnostics_path": diagnostics_path,
        "diagnostics": diagnostics,
        "manifest": manifest,
    }


def generate_comparison_report(
    results: List[Dict[str, Any]],
    out_dir: str,
) -> None:
    """Generate structured comparison report between B0, B1_PCA, and B1_IForest."""
    summary_table: List[Dict[str, Any]] = []

    for r in results:
        diag = r["diagnostics"]
        m = diag.get("metrics", {})
        cm = diag.get("confusion_matrix", {})
        oracle = diag.get("oracle_diagnostic", {})

        row = {
            "dataset": r["dataset"],
            "baseline": r["baseline"],
            "threshold": round(r["threshold"], 6),
            "flagged_windows": diag.get("flagged_windows_count", 0),
            "calib_anomalies": diag.get("total_anomalies", 0),
            "tp": cm.get("tp", 0),
            "fp": cm.get("fp", 0),
            "fn": cm.get("fn", 0),
            "precision": round(m.get("precision", 0.0), 4),
            "recall": round(m.get("recall", 0.0), 4),
            "f1": round(m.get("f1", 0.0), 4),
            "roc_auc": round(m["roc_auc"], 4) if m.get("roc_auc") is not None else None,
            "pr_auc": round(m["pr_auc"], 4) if m.get("pr_auc") is not None else None,
            "oracle_best_f1": round(oracle.get("f1", 0.0), 4),
            "oracle_best_threshold": round(oracle.get("threshold", 0.0), 6),
        }
        summary_table.append(row)

    # Save JSON report
    report_json_path = os.path.join(out_dir, "comparison_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "CALIBRATION SPLIT ONLY. TEST SPLIT IS FROZEN AND NOT EVALUATED.",
            "baselines": summary_table,
        }, f, indent=2)

    # Save Markdown report
    report_md_path = os.path.join(out_dir, "comparison_report.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 3 Unsupervised Baselines Comparison Report\n\n")
        f.write("> **IMPORTANT GUARDRAIL NOTE**: All metrics reported below are computed strictly on the **CALIBRATION** partition. The **TEST** partition remains completely frozen and was NOT accessed or evaluated, in strict accordance with Rule 1.\n\n")
        f.write("## Calibration Diagnostics Summary (Unsupervised Threshold at 95th Percentile)\n\n")
        f.write("| Dataset | Baseline | Threshold | Flagged | TP | FP | FN | Precision | Recall | F1 | ROC-AUC | PR-AUC | Oracle F1 (Diag) |\n")
        f.write("|---------|----------|-----------|---------|----|----|----|-----------|--------|----|---------|--------|------------------|\n")
        for row in summary_table:
            roc_str = f"{row['roc_auc']:.4f}" if row['roc_auc'] is not None else "N/A"
            pr_str = f"{row['pr_auc']:.4f}" if row['pr_auc'] is not None else "N/A"
            f.write(
                f"| {row['dataset'].upper()} | {row['baseline']} | {row['threshold']:.4f} | "
                f"{row['flagged_windows']} | {row['tp']} | {row['fp']} | {row['fn']} | "
                f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
                f"{roc_str} | {pr_str} | {row['oracle_best_f1']:.4f} |\n"
            )
        f.write("\n## Key Observations\n")
        f.write("1. **Unsupervised Thresholding**: Decision thresholds are derived purely as the 95th percentile of calibration scores without using ground-truth labels.\n")
        f.write("2. **Oracle Comparison**: The oracle F1 represents the theoretical maximum F1 achievable on calibration by searching over candidate thresholds with supervised hindsight.\n")
        f.write("3. **BGL Slice Context**: In the 50K development slice, BGL has 36 anomalous calibration windows and 0 anomalous test windows. Baselines are evaluated on BGL calibration for behavioral inspection only.\n")


def execute_baselines(
    config_path: str = "configs/baselines.yaml",
    dataset_filter: Optional[str] = None,
    baseline_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute Phase 3 baselines pipeline."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    data_dirs = config.get("data_dirs", {
        "hdfs": "data/processed/hdfs",
        "bgl": "data/processed/bgl",
    })
    output_dir = config.get("output_dir", "results/phase3")
    os.makedirs(output_dir, exist_ok=True)

    datasets = config.get("datasets", ["hdfs", "bgl"])
    if dataset_filter and dataset_filter.lower() != "all":
        datasets = [dataset_filter.lower()]

    baseline_types = ["b0", "b1_pca", "b1_iforest"]
    if baseline_filter and baseline_filter.lower() != "all":
        baseline_types = [baseline_filter.lower()]

    all_results: List[Dict[str, Any]] = []

    for ds in datasets:
        ds_dir = data_dirs.get(ds)
        if not ds_dir or not os.path.exists(ds_dir):
            print(f"Skipping dataset '{ds}': directory not found ({ds_dir})")
            continue

        train_path = os.path.join(ds_dir, "train.jsonl")
        calib_path = os.path.join(ds_dir, "calibration.jsonl")

        print(f"\n[{ds.upper()}] Loading TRAIN ({train_path}) and CALIBRATION ({calib_path})...")
        train_windows = load_windows(train_path, "train")
        calib_windows = load_windows(calib_path, "calibration")
        print(f"[{ds.upper()}] Loaded {len(train_windows)} train windows, {len(calib_windows)} calibration windows.")

        for b_type in baseline_types:
            print(f"[{ds.upper()}] Running baseline: {b_type}...")
            res = run_single_baseline(
                dataset=ds,
                baseline_type=b_type,
                train_windows=train_windows,
                calib_windows=calib_windows,
                config=config,
                data_dir=ds_dir,
                out_dir=output_dir,
            )
            all_results.append(res)
            diag = res["diagnostics"]
            m = diag["metrics"]
            print(
                f"[{ds.upper()} - {res['baseline']}] Threshold={res['threshold']:.4f} | "
                f"Precision={m['precision']:.4f} | Recall={m['recall']:.4f} | F1={m['f1']:.4f}"
            )

    generate_comparison_report(all_results, output_dir)
    print(f"\n[PHASE 3] Execution complete. Results and comparison report saved to {output_dir}/")
    return all_results


def main():
    """CLI entrypoint for Phase 3 baselines."""
    parser = argparse.ArgumentParser(description="SentinelLog Phase 3 Unsupervised Baselines Runner")
    parser.add_argument("--config", type=str, default="configs/baselines.yaml", help="Path to baselines configuration YAML")
    parser.add_argument("--dataset", type=str, default="all", choices=["hdfs", "bgl", "all"], help="Dataset to run")
    parser.add_argument("--baseline", type=str, default="all", choices=["b0", "b1_pca", "b1_iforest", "all"], help="Baseline to run")

    args = parser.parse_args()
    execute_baselines(
        config_path=args.config,
        dataset_filter=args.dataset,
        baseline_filter=args.baseline,
    )


if __name__ == "__main__":
    main()
