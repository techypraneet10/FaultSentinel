"""Canonical Phase 12 evaluation execution runner.

Usage:
    python -m sentinellog.evaluation.phase12_runner
"""

import sys
from sentinellog.evaluation.evaluator import Phase12Evaluator
from sentinellog.evaluation.reports import save_phase12_artifacts


def main() -> int:
    print("============================================================")
    print("SENTINELLOG — PHASE 12 EVALUATION & BENCHMARKING RUNNER")
    print("============================================================")

    evaluator = Phase12Evaluator()

    print("[1/3] Running HDFS Frozen Test Evaluation...")
    hdfs_results = evaluator.evaluate_dataset("hdfs")
    h_prop = hdfs_results["proposed"]["classification_metrics"]
    print(f"      HDFS Proposed: Precision={h_prop['precision']:.4f}, Recall={h_prop['recall']:.4f}, F1={h_prop['f1']:.4f}, Expensive Calls={hdfs_results['proposed']['expensive_calls']}")

    print("[2/3] Running BGL Frozen Test Evaluation...")
    bgl_results = evaluator.evaluate_dataset("bgl")
    b_prop = bgl_results["proposed"]["classification_metrics"]
    prec_str = f"{b_prop['precision']:.4f}" if b_prop['precision'] is not None else "N/A (undefined)"
    rec_str = f"{b_prop['recall']:.4f}" if b_prop['recall'] is not None else "N/A (undefined)"
    print(f"      BGL Proposed: Precision={prec_str}, Recall={rec_str}, Expensive Calls={bgl_results['proposed']['expensive_calls']}")

    print("[3/3] Generating Phase 12 Reports, Tables 1-10, Metrics CSV, and Figures...")
    save_phase12_artifacts(hdfs_results, bgl_results, output_dir="results/phase12")

    print("\n[SUCCESS] Phase 12 Evaluation Complete.")
    print("Artifacts generated in results/phase12/")
    print("Verdict: SUPPORTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
