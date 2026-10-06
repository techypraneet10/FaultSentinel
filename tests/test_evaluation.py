"""Comprehensive test suite for Phase 12 Evaluation & Benchmarking.

Validates:
- Classification and selective metrics correctness
- Conformal false-clear rate definitions vs miscoverage
- Wilson score confidence intervals and bootstrap determinism
- McNemar paired significance tests
- Cost model and expensive-call reduction calculation
- Test set locking and mutation prevention
- Corpus leakage audit (cross-split isolation)
- Experiment manifests and deterministic hashing
- Baseline scorer loading and evaluation on frozen test partitions
- SVG chart generators
- Regression protection for HDFS and BGL
"""

import json
import os
from pathlib import Path
import pytest
import numpy as np

from sentinellog.evaluation.baselines import load_all_baseline_scorers, score_and_classify
from sentinellog.evaluation.cost import evaluate_cost_model
from sentinellog.evaluation.curves import generate_precision_at_coverage, generate_risk_coverage_curve
from sentinellog.evaluation.evaluator import Phase12Evaluator
from sentinellog.evaluation.leakage import (
    TestMutationViolationError,
    TestSetLock,
    audit_corpus_leakage,
    guard_evaluation_only,
)
from sentinellog.evaluation.manifests import (
    build_evaluation_manifest,
    compute_deterministic_hash,
)
from sentinellog.evaluation.metrics import (
    compute_classification_metrics,
    compute_pr_auc,
    compute_roc_auc,
    compute_selective_metrics,
)
from sentinellog.evaluation.registry import ExperimentRegistry
from sentinellog.evaluation.reports import (
    build_phase12_report_markdown,
    generate_svg_bar_chart,
    generate_svg_line_chart,
)
from sentinellog.evaluation.statistics import (
    bootstrap_ci,
    compute_effect_sizes,
    mcnemar_test,
    wilson_score_interval,
)
from sentinellog.ingestion.schemas import LogWindow


def make_dummy_window(wid: str, is_anomaly: bool) -> LogWindow:
    return LogWindow(
        dataset="test_ds",
        window_id=wid,
        session_id=f"sess_{wid}",
        start_time=0.0,
        end_time=1.0,
        record_count=1,
        template_ids=[2],
        raw_messages=["dummy message"],
        is_anomaly=is_anomaly,
    )


# ---------------------------------------------------------------------------
# 1. Metric Calculations
# ---------------------------------------------------------------------------


def test_classification_metrics_perfect_predictions():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 1, 0, 0]
    m = compute_classification_metrics(y_true, y_pred)
    assert m.tp == 2
    assert m.tn == 2
    assert m.fp == 0
    assert m.fn == 0
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0
    assert m.fpr == 0.0
    assert m.empirical_false_clear_rate == 0.0


def test_classification_metrics_all_negative():
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    m = compute_classification_metrics(y_true, y_pred)
    assert m.tn == 3
    assert m.tp == 0
    assert m.precision is None
    assert m.recall is None
    assert m.f1 is None
    assert m.accuracy == 1.0


def test_classification_metrics_zero_prevalence_predicted_positive():
    y_true = [0, 0, 0]
    y_pred = [1, 0, 0]
    m = compute_classification_metrics(y_true, y_pred)
    assert m.precision == 0.0  # predicted positives > 0, TP = 0
    assert m.recall is None  # no ground-truth positives
    assert m.f1 is None


def test_classification_metrics_all_positive_predictions():
    y_true = [1, 0, 0, 0]
    y_pred = [1, 1, 1, 1]
    m = compute_classification_metrics(y_true, y_pred)
    assert m.tp == 1
    assert m.fp == 3
    assert m.fn == 0
    assert m.precision == 0.25
    assert m.recall == 1.0
    assert m.fpr == 1.0


def test_classification_metrics_imbalanced():
    y_true = [1] * 10 + [0] * 90
    y_pred = [1] * 5 + [0] * 5 + [1] * 5 + [0] * 85
    m = compute_classification_metrics(y_true, y_pred)
    assert m.tp == 5
    assert m.fn == 5
    assert m.fp == 5
    assert m.tn == 85
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.f1 == 0.5
    assert m.empirical_false_clear_rate == 0.05


def test_classification_metrics_zero_division_safety():
    y_true = [0, 0]
    y_pred = [0, 0]
    m = compute_classification_metrics(y_true, y_pred)
    assert m.precision is None
    assert m.recall is None
    assert m.f1 is None


def test_classification_metrics_length_mismatch_raises():
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_classification_metrics([1, 0], [1])


def test_classification_metrics_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        compute_classification_metrics([], [])


# ---------------------------------------------------------------------------
# 2. Selective Prediction Metrics
# ---------------------------------------------------------------------------


def test_selective_metrics_escalate_and_clear_counts():
    y_true = [1, 0, 1, 0]
    scores = [2.5, 0.5, 3.0, 0.2]
    sel = compute_selective_metrics(y_true, scores, threshold=1.0, strict=True)
    assert sel.total_windows == 4
    assert sel.escalated_windows == 2
    assert sel.cleared_windows == 2
    assert sel.escalation_rate == 0.5
    assert sel.auto_clear_rate == 0.5
    assert sel.anomalies_escalated == 2
    assert sel.anomalies_cleared == 0
    assert sel.empirical_false_clear_rate == 0.0
    assert sel.precision_escalated == 1.0


def test_selective_metrics_strict_vs_non_strict():
    y_true = [0, 1]
    scores = [1.0, 1.0]
    strict_sel = compute_selective_metrics(y_true, scores, threshold=1.0, strict=True)
    assert strict_sel.escalated_windows == 0
    assert strict_sel.cleared_windows == 2

    non_strict_sel = compute_selective_metrics(y_true, scores, threshold=1.0, strict=False)
    assert non_strict_sel.escalated_windows == 2
    assert non_strict_sel.cleared_windows == 0


def test_selective_metrics_empirical_false_clear_rate_formula():
    # 10 windows, 2 anomalies auto-cleared -> FN / N = 2 / 10 = 0.2
    y_true = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    sel = compute_selective_metrics(y_true, scores, threshold=0.5, strict=True)
    assert sel.anomalies_cleared == 2
    assert sel.empirical_false_clear_rate == 0.2
    assert sel.selective_risk == 2 / 5  # 2 false clears among 5 cleared


def test_selective_metrics_length_mismatch_raises():
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_selective_metrics([1, 0], [0.5], threshold=0.1)


# ---------------------------------------------------------------------------
# 3. AUC Metrics
# ---------------------------------------------------------------------------


def test_pr_auc_calculation_synthetic():
    y_true = [1, 1, 0, 0]
    scores = [0.9, 0.8, 0.2, 0.1]
    pr = compute_pr_auc(y_true, scores)
    assert pr is not None
    assert 0.9 <= pr <= 1.0


def test_roc_auc_calculation_synthetic():
    y_true = [1, 1, 0, 0]
    scores = [0.9, 0.8, 0.2, 0.1]
    roc = compute_roc_auc(y_true, scores)
    assert roc == 1.0


def test_auc_single_class_edge_cases():
    assert compute_pr_auc([0, 0, 0], [0.1, 0.2, 0.3]) is None
    assert compute_roc_auc([0, 0, 0], [0.1, 0.2, 0.3]) is None


# ---------------------------------------------------------------------------
# 4. Statistical Inference & Confidence Intervals
# ---------------------------------------------------------------------------


def test_wilson_score_interval_bounds():
    lower, upper = wilson_score_interval(50, 100, confidence=0.95)
    assert 0.0 < lower < 0.5
    assert 0.5 < upper < 1.0


def test_wilson_score_interval_zero_events():
    lower, upper = wilson_score_interval(0, 100, confidence=0.95)
    assert lower == 0.0
    assert 0.0 < upper < 0.05


def test_wilson_score_interval_all_events():
    lower, upper = wilson_score_interval(100, 100, confidence=0.95)
    assert 0.95 < lower < 1.0
    assert upper == 1.0


def test_wilson_score_interval_invalid_n():
    assert wilson_score_interval(0, 0) == (None, None)
    assert wilson_score_interval(None, 100) == (None, None)


def test_bootstrap_ci_determinism():
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    ci1 = bootstrap_ci(data, np.mean, n_resamples=500, seed=42)
    ci2 = bootstrap_ci(data, np.mean, n_resamples=500, seed=42)
    assert ci1 == ci2
    assert ci1[0] < np.mean(data) < ci1[1]


def test_mcnemar_test_identical_classifiers():
    y_pred = [1, 0, 1, 0]
    res = mcnemar_test(y_pred, y_pred)
    assert res["b"] == 0
    assert res["c"] == 0
    assert res["p_value"] == 1.0
    assert res["contingency_table"]["pos_a_neg_b"] == 0
    assert res["contingency_table"]["neg_a_pos_b"] == 0


def test_mcnemar_test_discordant_pairs():
    y_true = [1, 1, 1, 1, 0, 0]
    y_pred_a = [1, 1, 1, 1, 0, 0]
    y_pred_b = [0, 0, 0, 0, 1, 1]
    res = mcnemar_test(y_pred_a, y_pred_b, y_true=y_true)
    assert res["b"] == 4
    assert res["c"] == 2
    assert res["contingency_table"]["pos_a_neg_b"] == 4
    assert res["contingency_table"]["neg_a_pos_b"] == 2
    assert res["accuracy_discordant"]["b_a_correct_b_incorrect"] == 6
    assert res["accuracy_discordant"]["c_a_incorrect_b_correct"] == 0


def test_effect_sizes_computation():
    base = {"precision": 0.1, "recall": 0.8, "fpr": 0.5, "empirical_false_clear_rate": 0.02, "expensive_calls": 100}
    prop = {"precision": 0.4, "recall": 0.7, "fpr": 0.05, "empirical_false_clear_rate": 0.03, "expensive_calls": 20}
    eff = compute_effect_sizes(base, prop)
    assert eff["delta_precision"] == pytest.approx(0.3)
    assert eff["delta_recall"] == pytest.approx(-0.1)
    assert eff["delta_fpr"] == pytest.approx(-0.45)
    assert eff["expensive_call_reduction_ratio"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# 5. Curves & Sweeps
# ---------------------------------------------------------------------------


def test_precision_at_coverage_sweep():
    y_true = [1, 1, 0, 0, 0]
    scores = [2.0, 1.5, 0.8, 0.5, 0.1]
    thresholds = [1.8, 1.0, 0.4]
    names = ["high", "mid", "low"]
    pts = generate_precision_at_coverage(y_true, scores, thresholds, names, strict=True)
    assert len(pts) == 3
    assert pts[0]["operating_point"] == "high"
    assert pts[0]["precision"] == 1.0  # only 2.0 escalated -> TP=1, FP=0
    assert pts[2]["operating_point"] == "low"
    assert pts[2]["precision"] == 0.5  # 4 escalated (2 TP, 2 FP)


def test_risk_coverage_curve_generation():
    y_true = [1, 0, 0, 1]
    scores = [1.0, 0.5, 0.2, 0.8]
    grid = [0.1, 0.6, 0.9]
    curve = generate_risk_coverage_curve(y_true, scores, grid)
    assert len(curve) == 3
    for pt in curve:
        assert "auto_clear_coverage" in pt
        assert "selective_risk" in pt


# ---------------------------------------------------------------------------
# 6. Cost Model
# ---------------------------------------------------------------------------


def test_cost_model_b3_all_windows_expensive():
    cost = evaluate_cost_model(total_windows=100, escalated_windows=100)
    assert cost.expensive_calls == 100
    assert cost.expensive_call_fraction == 1.0
    assert cost.llm_call_reduction_ratio == 0.0
    assert cost.relative_cost_reduction_ratio == 0.0


def test_cost_model_selective_escalated_calls_only():
    cost = evaluate_cost_model(total_windows=100, escalated_windows=5)
    assert cost.expensive_calls == 5
    assert cost.expensive_call_fraction == 0.05
    assert cost.llm_call_reduction_ratio == 0.95
    assert cost.relative_cost_reduction_ratio > 0.8


def test_cost_model_invalid_inputs_raise():
    with pytest.raises(ValueError):
        evaluate_cost_model(total_windows=0, escalated_windows=0)


# ---------------------------------------------------------------------------
# 7. Test-Set Locking & Leakage Protection
# ---------------------------------------------------------------------------


def test_test_set_lock_prevents_fit_on_test():
    with pytest.raises(TestMutationViolationError, match="Rule 1 Violation"):
        with TestSetLock(split_name="test", operation="fit"):
            pass


def test_test_set_lock_prevents_calibrate_on_test():
    with pytest.raises(TestMutationViolationError, match="Rule 1 Violation"):
        guard_evaluation_only(operation="calibrate", split_name="test")


def test_test_set_lock_allows_evaluate_on_test():
    with TestSetLock(split_name="test", operation="evaluate"):
        pass  # Should not raise


def test_corpus_leakage_audit_clean_splits():
    train_w = [make_dummy_window("tr_1", False), make_dummy_window("tr_2", False)]
    calib_w = [make_dummy_window("cal_1", False)]
    test_w = [make_dummy_window("te_1", False)]

    rep = audit_corpus_leakage(train_w, calib_w, test_w, retrieval_window_ids={"tr_1", "tr_2"})
    assert rep["passed"] is True
    assert rep["retrieval_corpus_clean"] is True


def test_corpus_leakage_audit_detects_test_in_train():
    train_w = [make_dummy_window("leak_1", False)]
    calib_w = [make_dummy_window("cal_1", False)]
    test_w = [make_dummy_window("leak_1", False)]

    rep = audit_corpus_leakage(train_w, calib_w, test_w)
    assert rep["passed"] is False
    assert rep["train_test_overlap_count"] == 1


def test_corpus_leakage_audit_detects_test_in_retrieval():
    train_w = [make_dummy_window("tr_1", False)]
    calib_w = [make_dummy_window("cal_1", False)]
    test_w = [make_dummy_window("te_1", False)]

    rep = audit_corpus_leakage(train_w, calib_w, test_w, retrieval_window_ids={"te_1"})
    assert rep["passed"] is False
    assert rep["retrieval_test_overlap_count"] == 1


# ---------------------------------------------------------------------------
# 8. Manifests & Registry
# ---------------------------------------------------------------------------


def test_experiment_manifest_separates_scientific_and_runtime():
    man = build_evaluation_manifest(
        experiment_id="test_exp_01",
        dataset="hdfs",
        split="test",
        model_name="test_model",
        parameters={"alpha": 0.05},
        metrics={"f1": 0.5},
    )
    assert "scientific_hash" in man
    assert "scientific_payload" in man
    assert "runtime_metadata" in man
    assert "git_commit" in man["runtime_metadata"]
    # Scientific payload must NOT contain volatile git commit or timestamps
    assert "git_commit" not in man["scientific_payload"]


def test_experiment_manifest_hash_reproducibility():
    payload = {"dataset": "hdfs", "f1": 0.5, "model": "B2"}
    h1 = compute_deterministic_hash(payload)
    h2 = compute_deterministic_hash(payload)
    assert h1 == h2


def test_experiment_registry_writes_canonical_files(tmp_path):
    reg = ExperimentRegistry(str(tmp_path))
    exp_dir = reg.register_experiment(
        experiment_id="exp_hdfs_01",
        config={"dataset": "hdfs"},
        manifest={"hash": "abc"},
        metrics={"f1": 0.8},
        confusion_matrix={"tp": 10, "fp": 2, "tn": 80, "fn": 8},
        provenance_metadata={"split": "test"},
    )
    assert (exp_dir / "config.json").exists()
    assert (exp_dir / "manifest.json").exists()
    assert (exp_dir / "metrics.json").exists()
    assert (exp_dir / "confusion_matrix.json").exists()
    assert (exp_dir / "provenance_metadata.json").exists()


# ---------------------------------------------------------------------------
# 9. Baseline Scorer Loading & Execution
# ---------------------------------------------------------------------------


def test_baseline_scorers_loading_hdfs():
    train_windows = [
        LogWindow.from_dict(json.loads(line))
        for line in open("data/processed/hdfs/train.jsonl", "r", encoding="utf-8")
    ][:20]
    scorers = load_all_baseline_scorers("hdfs", train_windows)
    assert "b0" in scorers
    assert "b1_pca" in scorers
    assert "b1_iforest" in scorers
    assert "b2" in scorers
    assert scorers["b2"]["thresholds_alpha_grid"][0.05] == 1.1545928716659546


def test_score_and_classify_execution():
    train_windows = [
        LogWindow.from_dict(json.loads(line))
        for line in open("data/processed/hdfs/train.jsonl", "r", encoding="utf-8")
    ][:10]
    scorers = load_all_baseline_scorers("hdfs", train_windows)
    sc, preds = score_and_classify(scorers["b0"]["scorer"], train_windows, threshold=1.0)
    assert len(sc) == 10
    assert len(preds) == 10
    assert set(preds).issubset({0, 1})


# ---------------------------------------------------------------------------
# 10. Phase 12 Evaluator & End-to-End Benchmarks
# ---------------------------------------------------------------------------


def test_phase12_evaluator_hdfs_test_run(tmp_path):
    evaluator = Phase12Evaluator(output_dir=str(tmp_path))
    res = evaluator.evaluate_dataset("hdfs")

    assert res["dataset"] == "hdfs"
    assert res["total_windows"] == 823
    assert res["total_anomalies"] == 30
    assert res["leakage_audit"]["passed"] is True

    # Baselines present
    assert "b0" in res["baselines"]
    assert "b1_pca" in res["baselines"]
    assert "b1_iforest" in res["baselines"]
    assert "b2" in res["baselines"]
    assert "b3" in res["baselines"]

    # Proposed system present
    prop = res["proposed"]
    assert prop["expensive_calls"] == 43
    assert prop["classification_metrics"]["precision"] > res["baselines"]["b1_pca"]["metrics"]["precision"]
    assert prop["cost_accounting"]["llm_call_reduction_ratio"] > 0.90


def test_phase12_evaluator_bgl_test_run(tmp_path):
    evaluator = Phase12Evaluator(output_dir=str(tmp_path))
    res = evaluator.evaluate_dataset("bgl")

    assert res["dataset"] == "bgl"
    assert res["total_windows"] == 100
    assert res["leakage_audit"]["passed"] is True

    # BGL safety check: 0 windows escalated, 0 false alarms, 0 expensive calls
    prop = res["proposed"]
    assert prop["expensive_calls"] == 0
    assert prop["classification_metrics"]["fp"] == 0


def test_bgl_safety_case_zero_false_alarms():
    evaluator = Phase12Evaluator()
    res = evaluator.evaluate_dataset("bgl")
    # Proposed system must trigger 0 false alarms on BGL test slice
    assert res["proposed"]["classification_metrics"]["fp"] == 0
    assert res["proposed"]["classification_metrics"]["tp"] == 0
    assert res["proposed"]["expensive_calls"] == 0


def test_hdfs_selective_reduces_expensive_calls_over_90_percent():
    evaluator = Phase12Evaluator()
    res = evaluator.evaluate_dataset("hdfs")
    cost = res["proposed"]["cost_accounting"]
    assert cost["llm_call_reduction_ratio"] >= 0.94


def test_phase12_report_markdown_contains_all_10_tables():
    evaluator = Phase12Evaluator()
    hdfs_res = evaluator.evaluate_dataset("hdfs")
    bgl_res = evaluator.evaluate_dataset("bgl")
    md = build_phase12_report_markdown(hdfs_res, bgl_res, verdict="SUPPORTED")

    for i in range(1, 11):
        assert f"TABLE {i}" in md
    assert "VERDICT:" in md
    assert "SUPPORTED" in md


def test_svg_bar_chart_generation(tmp_path):
    out = str(tmp_path / "test_bar.svg")
    generate_svg_bar_chart("Test Bar", ["A", "B"], [10.0, 20.0], "Count", out)
    assert os.path.exists(out)
    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<svg" in content
        assert "Test Bar" in content


def test_svg_line_chart_generation(tmp_path):
    out = str(tmp_path / "test_line.svg")
    generate_svg_line_chart("Test Line", [0.1, 0.5, 0.9], [1.0, 2.0, 3.0], "X", "Y", out)
    assert os.path.exists(out)
    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<svg" in content
        assert "Test Line" in content


def test_mcnemar_contingency_table_from_saved_predictions():
    """Regression test connecting paired 2x2 contingency table to saved predictions."""
    evaluator = Phase12Evaluator()
    evaluator.evaluate_dataset("hdfs")

    pred_path = Path("results/phase12/hdfs_predictions.json")
    assert pred_path.exists(), "results/phase12/hdfs_predictions.json must exist"

    with open(pred_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    b0_preds = np.asarray(data["b0"], dtype=int)
    sent_preds = np.asarray(data["sentinellog"], dtype=int)
    y_true = np.asarray(data["y_true"], dtype=int)

    # Compute contingency table directly from saved predictions
    b0_pos = (b0_preds == 1)
    sent_pos = (sent_preds == 1)

    n11 = int(np.sum(b0_pos & sent_pos))
    n10 = int(np.sum(b0_pos & (~sent_pos)))
    n01 = int(np.sum((~b0_pos) & sent_pos))
    n00 = int(np.sum((~b0_pos) & (~sent_pos)))

    assert n11 == 12, f"Expected B0+ / Sentinel+ = 12, got {n11}"
    assert n10 == 400, f"Expected B0+ / Sentinel- = 400, got {n10}"
    assert n01 == 31, f"Expected B0- / Sentinel+ = 31, got {n01}"
    assert n00 == 380, f"Expected B0- / Sentinel- = 380, got {n00}"
    assert n11 + n10 + n01 + n00 == 823

    # Check McNemar test outputs match exactly
    res = mcnemar_test(b0_preds, sent_preds, y_true=y_true)
    assert res["contingency_table"]["pos_a_pos_b"] == 12
    assert res["contingency_table"]["pos_a_neg_b"] == 400
    assert res["contingency_table"]["neg_a_pos_b"] == 31
    assert res["contingency_table"]["neg_a_neg_b"] == 380
    assert res["b"] == 400
    assert res["c"] == 31
    expected_stat = ((abs(400 - 31) - 1.0) ** 2) / (400 + 31)
    assert abs(res["statistic"] - expected_stat) < 1e-4
    assert res["p_value"] < 1e-60


def test_bgl_zero_prevalence_metrics_undefined():
    """Verify BGL zero-prevalence partition produces None (undefined) for recall, F1, and precision where appropriate."""
    evaluator = Phase12Evaluator()
    res = evaluator.evaluate_dataset("bgl")
    b0_m = res["baselines"]["b0"]["metrics"]
    prop_m = res["proposed"]["classification_metrics"]

    assert b0_m["recall"] is None
    assert b0_m["f1"] is None
    assert b0_m["precision"] is None  # predicted positives == 0

    assert prop_m["recall"] is None
    assert prop_m["f1"] is None
    assert prop_m["precision"] is None  # predicted positives == 0

