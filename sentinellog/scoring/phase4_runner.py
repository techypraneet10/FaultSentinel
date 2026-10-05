"""Phase 4 execution engine and CLI runner.

Coordinates:
1. B2 Sequential GRU training strictly on TRAIN.
2. Inductive Split Conformal Calibration on CALIBRATION.
3. Selective Gate evaluation across nominal alpha grid.
4. Ablations (Heuristic vs Conformal, B1 PCA vs B2, Calibration sample size sensitivity).
5. Generation of experiment manifests, diagnostics, and reports.

Rule 1 (Test Set Protection) is strictly enforced: TEST is never loaded or accessed.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import torch
import yaml

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import (
    SelectiveGate,
    evaluate_selective_performance,
    sweep_alpha_grid,
)
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.scoring.artifacts import (
    compute_sha256,
    get_git_commit_sha,
    guard_no_test_split,
)
from sentinellog.scoring.b1 import PCAScorer
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.baselines import load_windows
from sentinellog.scoring.thresholds import compute_unsupervised_threshold


def run_phase4_dataset(
    dataset: str,
    train_windows: List[LogWindow],
    calib_windows: List[LogWindow],
    config: Dict[str, Any],
    data_dir: str,
    output_dir: str,
) -> Dict[str, Any]:
    """Execute complete Phase 4 pipeline for a single dataset."""
    git_sha = get_git_commit_sha()
    manifest_path = os.path.join(data_dir, "manifest.json")
    data_hash = compute_sha256(manifest_path) if os.path.exists(manifest_path) else "MISSING"

    start_time = time.perf_counter()

    # 1. Initialize B2 Sequential Scorer
    model_cfg = config.get("model", {})
    train_cfg = config.get("training", {})
    conf_cfg = config.get("conformal", {})
    abl_cfg = config.get("ablations", {})

    seed = config.get("random_seed", 42)

    scorer = B2SequentialScorer(
        embedding_dim=model_cfg.get("embedding_dim", 32),
        hidden_dim=model_cfg.get("hidden_dim", 64),
        num_layers=model_cfg.get("num_layers", 1),
        dropout=model_cfg.get("dropout", 0.1),
        max_seq_len=model_cfg.get("max_seq_len", 100),
        train_normal_only=train_cfg.get("train_normal_only", True),
        val_ratio=train_cfg.get("val_ratio", 0.10),
        batch_size=train_cfg.get("batch_size", 64),
        epochs=train_cfg.get("epochs", 20),
        patience=train_cfg.get("patience", 3),
        learning_rate=train_cfg.get("learning_rate", 0.001),
        weight_decay=train_cfg.get("weight_decay", 1e-4),
        random_state=seed,
    )

    print(f"[{dataset.upper()}] Training B2 Sequential GRU on TRAIN ({len(train_windows)} windows)...")
    scorer.fit(train_windows)
    fit_duration = time.perf_counter() - start_time

    # 2. Score CALIBRATION windows (Frozen model)
    print(f"[{dataset.upper()}] Scoring CALIBRATION windows ({len(calib_windows)} windows)...")
    score_start = time.perf_counter()
    calib_scores = scorer.score(calib_windows)
    score_duration = time.perf_counter() - score_start

    calib_labels = [1 if w.is_anomaly else 0 for w in calib_windows]

    # 3. Fit Split Conformal Calibrator
    calibrator = SplitConformalCalibrator(calib_scores)

    # 4. Target Alpha Sweep
    alpha_grid = conf_cfg.get("alpha_grid", [0.01, 0.05, 0.10, 0.20])
    strict = conf_cfg.get("strict", True)
    sweep_results = sweep_alpha_grid(
        scores=calib_scores,
        labels=calib_labels,
        calibrator=calibrator,
        alpha_grid=alpha_grid,
        strict=strict,
    )

    # 5. Ablation A: Heuristic Fixed-Quantile Threshold vs Conformal Gate
    fixed_q = abl_cfg.get("fixed_quantile", 0.95)
    heuristic_th = compute_unsupervised_threshold(calib_scores, quantile=fixed_q)
    heuristic_preds = [(s > heuristic_th if strict else s >= heuristic_th) for s in calib_scores]
    h_tp = sum(1 for p, y in zip(heuristic_preds, calib_labels) if p and y == 1)
    h_fp = sum(1 for p, y in zip(heuristic_preds, calib_labels) if p and y == 0)
    h_fn = sum(1 for p, y in zip(heuristic_preds, calib_labels) if not p and y == 1)
    h_tn = sum(1 for p, y in zip(heuristic_preds, calib_labels) if not p and y == 0)
    ablation_a = {
        "description": "B2 with Fixed Heuristic Quantile Threshold (No Conformal)",
        "fixed_quantile": fixed_q,
        "threshold": float(heuristic_th),
        "tp": h_tp,
        "fp": h_fp,
        "fn": h_fn,
        "tn": h_tn,
        "precision": float(h_tp / (h_tp + h_fp)) if (h_tp + h_fp) > 0 else 0.0,
        "recall": float(h_tp / (h_tp + h_fn)) if (h_tp + h_fn) > 0 else 0.0,
        "f1": float((2 * h_tp) / (2 * h_tp + h_fp + h_fn)) if (2 * h_tp + h_fp + h_fn) > 0 else 0.0,
        "escalation_rate": float((h_tp + h_fp) / len(calib_labels)),
        "coverage": float((h_tn + h_fn) / len(calib_labels)),
        "selective_risk": float(h_fn / (h_tn + h_fn)) if (h_tn + h_fn) > 0 else 0.0,
    }

    # 6. Ablation B: B1 PCA Comparison on same calibration split
    pca = PCAScorer(mode="normalized_count", variance_ratio=0.95, random_state=seed)
    pca.fit(train_windows)
    pca_scores = pca.score(calib_windows)
    pca_calibrator = SplitConformalCalibrator(pca_scores)
    pca_sweep = sweep_alpha_grid(
        scores=pca_scores,
        labels=calib_labels,
        calibrator=pca_calibrator,
        alpha_grid=alpha_grid,
        strict=strict,
    )
    ablation_b = {
        "description": "B1 PCA vs B2 Sequential GRU under identical conformal gate",
        "pca_sweep": pca_sweep,
    }

    # 7. Ablation C: Calibration Sample Size Sensitivity (Chronological subsets)
    calib_sizes = abl_cfg.get("calibration_sizes", [0.25, 0.50, 1.00])
    size_sensitivity: List[Dict[str, Any]] = []
    n_calib = len(calib_windows)

    for frac in calib_sizes:
        sub_n = max(5, int(n_calib * frac))
        # Strictly chronological prefix
        sub_scores = calib_scores[:sub_n]
        sub_labels = calib_labels[:sub_n]
        sub_calibrator = SplitConformalCalibrator(sub_scores)

        # Evaluate at alpha = 0.05
        sub_perf = evaluate_selective_performance(
            scores=sub_scores,
            labels=sub_labels,
            calibrator=sub_calibrator,
            alpha=0.05,
            strict=strict,
        )
        size_sensitivity.append({
            "fraction": frac,
            "sample_size": sub_n,
            "threshold_alpha_0_05": sub_perf["conformal_threshold"],
            "escalation_rate": sub_perf["escalation_rate"],
            "coverage": sub_perf["coverage"],
            "selective_risk": sub_perf["selective_risk"],
            "empirical_miscoverage": sub_perf["empirical_miscoverage"],
            "deviation": sub_perf["deviation_from_nominal"],
        })

    ablation_c = {
        "description": "Sensitivity of conformal threshold to chronological calibration sample size (alpha=0.05)",
        "results": size_sensitivity,
    }

    # 8. Save Artifacts & Manifest
    dataset_out_dir = os.path.join(output_dir, dataset)
    os.makedirs(dataset_out_dir, exist_ok=True)

    # Save PyTorch model state dict
    checkpoint_path = os.path.join(dataset_out_dir, "b2_model.pt")
    torch.save({
        "model_state_dict": scorer.model.state_dict(),
        "model_metadata": scorer.model.get_metadata(),
        "tokenizer_metadata": scorer.tokenizer.get_metadata(),
        "training_metadata": scorer.get_metadata(),
    }, checkpoint_path)

    # Save calibration diagnostics
    diagnostics = {
        "dataset": dataset,
        "n_train": len(train_windows),
        "n_calib": len(calib_windows),
        "calibrator_metadata": calibrator.get_metadata(),
        "alpha_sweep": sweep_results,
        "ablation_a_fixed_heuristic": ablation_a,
        "ablation_b_pca_vs_b2": ablation_b,
        "ablation_c_sample_size": ablation_c,
        "training_history": scorer.training_history_,
        "timing": {
            "fit_seconds": fit_duration,
            "scoring_seconds": score_duration,
            "total_seconds": time.perf_counter() - start_time,
        },
    }
    diag_path = os.path.join(dataset_out_dir, "conformal_diagnostics.json")
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)

    # Save manifest
    manifest = {
        "experiment": f"{dataset}_b2_conformal",
        "dataset": dataset,
        "baseline": "B2_SequentialGRU_Conformal",
        "git_commit": git_sha,
        "seed": seed,
        "data_manifest_hash": data_hash,
        "processing_version": config.get("version", "0.4.0-phase4"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "model_config": scorer.get_metadata(),
        "parameter_count": scorer.model.count_parameters(),
        "max_allowed_parameters": 2_000_000,
        "train_windows": len(train_windows),
        "calibration_windows": len(calib_windows),
        "test_used": False,  # Rule 1 Invariant
    }
    manifest_file_path = os.path.join(dataset_out_dir, "manifest.json")
    with open(manifest_file_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "dataset": dataset,
        "diagnostics": diagnostics,
        "manifest": manifest,
        "checkpoint_path": checkpoint_path,
        "diag_path": diag_path,
        "manifest_path": manifest_file_path,
    }


def generate_phase4_report(
    results: List[Dict[str, Any]],
    output_dir: str,
) -> None:
    """Generate comprehensive markdown and JSON report for Phase 4."""
    report_json_path = os.path.join(output_dir, "phase4_report.json")
    report_md_path = os.path.join(output_dir, "phase4_report.md")

    # Serialize JSON
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "CALIBRATION SPLIT ONLY. TEST SPLIT FROZEN AND UNTOUCHED.",
            "results": [r["diagnostics"] for r in results],
        }, f, indent=2)

    # Format Markdown
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 4: Learned Sequential Scorer + Conformal Selective Gate Report\n\n")
        f.write("> **RESEARCH INTEGRITY GUARDRAIL**: All results are derived exclusively from **TRAIN** and **CALIBRATION** partitions. The **TEST** partition remains strictly **FROZEN** under Rule 1.\n\n")

        for r in results:
            ds = r["dataset"].upper()
            diag = r["diagnostics"]
            manifest = r["manifest"]
            m_meta = manifest["model_config"]["model_metadata"]

            f.write(f"## Dataset: {ds}\n\n")
            f.write(f"- **Architecture**: Sequential GRU (Embedding: {m_meta['embedding_dim']}, Hidden: {m_meta['hidden_dim']}, Layers: {m_meta['num_layers']})\n")
            f.write(f"- **Trainable Parameters**: {manifest['parameter_count']:,} (Constraint: < 2,000,000)\n")
            f.write(f"- **Training Epochs**: {len(diag['training_history'])} (Best Val Loss: {manifest['model_config']['best_val_loss']:.4f} at epoch {manifest['model_config']['best_epoch']})\n")
            f.write(f"- **Calibration Sample Size ($n$)**: {diag['n_calib']}\n\n")

            f.write("### Target Alpha Sweep (Split Conformal Calibration)\n\n")
            f.write("| Nominal $\\alpha$ | Threshold $\\hat{\\tau}_\\alpha$ | Escalated | Coverage | Escalation Precision | Escalation Recall | False Clears | Selective Risk | Empirical Miscoverage | Deviation |\n")
            f.write("|---|---|---|---|---|---|---|---|---|---|\n")

            for sw in diag["alpha_sweep"]:
                cm = sw["confusion_matrix"]
                f.write(
                    f"| {sw['nominal_alpha']:.2f} | {sw['conformal_threshold']:.4f} | "
                    f"{sw['n_escalated']} ({sw['escalation_rate']:.1%}) | {sw['coverage']:.1%} | "
                    f"{sw['escalation_precision']:.4f} | {sw['escalation_recall']:.4f} | "
                    f"{sw['false_clears_count']} | {sw['selective_risk']:.4f} | "
                    f"{sw['empirical_miscoverage']:.4f} | {sw['deviation_from_nominal']:+.4f} |\n"
                )

            f.write("\n### Ablation Summary\n\n")
            abl_a = diag["ablation_a_fixed_heuristic"]
            f.write(f"1. **Ablation A (Heuristic Threshold vs Conformal)**: Fixed 95th-percentile threshold flags {abl_a['escalation_rate']:.1%} of windows (Precision: {abl_a['precision']:.4f}, Recall: {abl_a['recall']:.4f}, Selective Risk: {abl_a['selective_risk']:.4f}).\n")

            f.write("2. **Ablation B (B1 PCA vs B2 Sequential GRU)**:\n\n")
            f.write("| Model | Nominal $\\alpha$ | Threshold | Escalation Rate | Coverage | Precision | Recall | Selective Risk |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")

            b2_by_alpha = {sw["nominal_alpha"]: sw for sw in diag["alpha_sweep"]}
            for pca_sw in diag["ablation_b_pca_vs_b2"]["pca_sweep"]:
                a_val = pca_sw["nominal_alpha"]
                b2_sw = b2_by_alpha.get(a_val, {})
                f.write(
                    f"| B1 PCA | {a_val:.2f} | {pca_sw['conformal_threshold']:.4f} | "
                    f"{pca_sw['escalation_rate']:.1%} | {pca_sw['coverage']:.1%} | "
                    f"{pca_sw['escalation_precision']:.4f} | {pca_sw['escalation_recall']:.4f} | "
                    f"{pca_sw['selective_risk']:.4f} |\n"
                )
                f.write(
                    f"| **B2 GRU** | {a_val:.2f} | {b2_sw.get('conformal_threshold', 0.0):.4f} | "
                    f"{b2_sw.get('escalation_rate', 0.0):.1%} | {b2_sw.get('coverage', 0.0):.1%} | "
                    f"{b2_sw.get('escalation_precision', 0.0):.4f} | {b2_sw.get('escalation_recall', 0.0):.4f} | "
                    f"{b2_sw.get('selective_risk', 0.0):.4f} |\n"
                )

            f.write("\n3. **Ablation C (Calibration Size Sensitivity at $\\alpha=0.05$)**:\n\n")
            f.write("| Fraction | Sample Size | Conformal $\\hat{\\tau}_{0.05}$ | Escalation Rate | Coverage | Selective Risk | Miscoverage |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for sz in diag["ablation_c_sample_size"]["results"]:
                f.write(
                    f"| {sz['fraction']:.0%} | {sz['sample_size']} | {sz['threshold_alpha_0_05']:.4f} | "
                    f"{sz['escalation_rate']:.1%} | {sz['coverage']:.1%} | "
                    f"{sz['selective_risk']:.4f} | {sz['empirical_miscoverage']:.4f} |\n"
                )
            f.write("\n---\n\n")


def execute_phase4(
    config_path: str = "configs/phase4.yaml",
    dataset_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute Phase 4 experiments."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    data_dirs = config.get("data_dirs", {
        "hdfs": "data/processed/hdfs",
        "bgl": "data/processed/bgl",
    })
    output_dir = config.get("output_dir", "results/phase4")
    os.makedirs(output_dir, exist_ok=True)

    datasets = config.get("datasets", ["hdfs", "bgl"])
    if dataset_filter and dataset_filter.lower() != "all":
        datasets = [dataset_filter.lower()]

    all_results: List[Dict[str, Any]] = []

    for ds in datasets:
        ds_dir = data_dirs.get(ds)
        if not ds_dir or not os.path.exists(ds_dir):
            print(f"Skipping dataset '{ds}': directory not found ({ds_dir})")
            continue

        train_path = os.path.join(ds_dir, "train.jsonl")
        calib_path = os.path.join(ds_dir, "calibration.jsonl")

        # RULE 1: Enforce test access guard
        guard_no_test_split("train", train_path)
        guard_no_test_split("calibration", calib_path)

        train_windows = load_windows(train_path, "train")
        calib_windows = load_windows(calib_path, "calibration")

        res = run_phase4_dataset(
            dataset=ds,
            train_windows=train_windows,
            calib_windows=calib_windows,
            config=config,
            data_dir=ds_dir,
            output_dir=output_dir,
        )
        all_results.append(res)

    generate_phase4_report(all_results, output_dir)
    print(f"\n[PHASE 4] Execution complete. Results saved to {output_dir}/")
    return all_results


def main():
    """CLI entrypoint for Phase 4."""
    parser = argparse.ArgumentParser(description="SentinelLog Phase 4 B2 + Conformal Gate Runner")
    parser.add_argument("--config", type=str, default="configs/phase4.yaml", help="Path to Phase 4 YAML config")
    parser.add_argument("--dataset", type=str, default="all", choices=["hdfs", "bgl", "all"], help="Dataset filter")
    args = parser.parse_args()

    execute_phase4(config_path=args.config, dataset_filter=args.dataset)


if __name__ == "__main__":
    main()
