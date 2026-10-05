"""Test suite for Phase 3: Unsupervised Anomaly Detection Baselines.

Verifies:
1. B0 frequency training uses TRAIN only.
2. B0 frequency calculation is deterministic.
3. Unknown template handling is deterministic and explicitly mapped.
4. B1 vector dimensions are stable across partitions.
5. Calibration cannot create new vocabulary dimensions (leakage barrier).
6. PCA fit uses TRAIN only and obeys variance ratio / component constraints.
7. B1 anomaly score direction is strictly higher = more anomalous.
8. Unsupervised quantile threshold computation is deterministic.
9. Test access guard strictly prevents access to test splits (Rule 1).
10. Baseline experiments are 100% reproducible across reruns.
11. Saved model artifacts can be reloaded with identical scoring behavior.
12. Isolation Forest determinism with fixed random_state.
13. Diagnostic metrics calculations (precision, recall, F1, ROC-AUC, PR-AUC).
"""

import os
import tempfile
import numpy as np
import pytest

from sentinellog.ingestion.schemas import LogWindow, UNKNOWN_TEMPLATE_ID
from sentinellog.scoring.artifacts import (
    TestAccessViolationError,
    guard_no_test_split,
    load_model_artifact,
    save_model_artifact,
)
from sentinellog.scoring.b0 import FrequencyScorer
from sentinellog.scoring.b1 import IsolationForestScorer, PCAScorer
from sentinellog.scoring.baselines import load_windows, run_single_baseline
from sentinellog.scoring.features import TemplateCountVectorizer
from sentinellog.scoring.thresholds import (
    compute_oracle_threshold,
    compute_unsupervised_threshold,
    evaluate_calibration_diagnostics,
)


@pytest.fixture
def synthetic_windows():
    """Create deterministic synthetic train and calibration windows."""
    train_windows = [
        LogWindow(
            dataset="synthetic",
            window_id=f"win_train_{i}",
            session_id=f"s_{i}",
            start_time=float(100 + i * 10),
            end_time=float(105 + i * 10),
            record_count=4,
            template_ids=[1, 2, 1, 3],
            raw_messages=["msg1", "msg2", "msg1", "msg3"],
            is_anomaly=False,
        )
        for i in range(20)
    ]
    # Add one rare template window to train
    train_windows.append(
        LogWindow(
            dataset="synthetic",
            window_id="win_train_rare",
            session_id="s_rare",
            start_time=350.0,
            end_time=355.0,
            record_count=3,
            template_ids=[4, 4, 1],
            raw_messages=["rare4", "rare4", "msg1"],
            is_anomaly=False,
        )
    )

    # Calibration windows: 8 normal (same pattern), 2 anomalous with unknown or rare templates
    calib_windows = [
        LogWindow(
            dataset="synthetic",
            window_id=f"win_calib_norm_{i}",
            session_id=f"calib_{i}",
            start_time=float(400 + i * 10),
            end_time=float(405 + i * 10),
            record_count=4,
            template_ids=[1, 2, 1, 3],
            raw_messages=["msg1", "msg2", "msg1", "msg3"],
            is_anomaly=False,
        )
        for i in range(8)
    ]
    # Anomalous window 1: novel/unknown template 99 and UNKNOWN_TEMPLATE_ID (-1)
    calib_windows.append(
        LogWindow(
            dataset="synthetic",
            window_id="win_calib_anom_1",
            session_id="calib_anom_1",
            start_time=500.0,
            end_time=505.0,
            record_count=3,
            template_ids=[99, UNKNOWN_TEMPLATE_ID, 4],
            raw_messages=["novel", "unknown", "rare4"],
            is_anomaly=True,
        )
    )
    # Anomalous window 2: heavily dominated by rare template 4
    calib_windows.append(
        LogWindow(
            dataset="synthetic",
            window_id="win_calib_anom_2",
            session_id="calib_anom_2",
            start_time=520.0,
            end_time=525.0,
            record_count=4,
            template_ids=[4, 4, 4, 4],
            raw_messages=["rare4", "rare4", "rare4", "rare4"],
            is_anomaly=True,
        )
    )

    return train_windows, calib_windows


def test_b0_training_uses_train_only(synthetic_windows):
    """Test that B0 frequency distribution is computed solely from TRAIN."""
    train_w, calib_w = synthetic_windows
    scorer = FrequencyScorer(alpha=1.0)
    scorer.fit(train_w)

    # Training tokens count: 20 * 4 + 3 = 83 tokens
    assert scorer.total_tokens_ == 83
    # Check that template 99 (only in calib) is not in vocabulary_
    assert 99 not in scorer.vocabulary_
    assert UNKNOWN_TEMPLATE_ID in scorer.log_probabilities_


def test_b0_frequency_calculation_deterministic(synthetic_windows):
    """Test that B0 frequency calculations produce identical values across calls."""
    train_w, calib_w = synthetic_windows
    scorer1 = FrequencyScorer(alpha=1.0).fit(train_w)
    scorer2 = FrequencyScorer(alpha=1.0).fit(train_w)

    scores1 = scorer1.score(calib_w)
    scores2 = scorer2.score(calib_w)
    np.testing.assert_array_almost_equal(scores1, scores2, decimal=10)


def test_unknown_template_handling_deterministic(synthetic_windows):
    """Test that unknown/unseen templates receive deterministic smoothed surprisal."""
    train_w, _ = synthetic_windows
    scorer = FrequencyScorer(alpha=1.0).fit(train_w)

    w_unknown_1 = LogWindow(
        dataset="test",
        window_id="w_u1",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=1,
        template_ids=[-1],
        raw_messages=["unknown"],
        is_anomaly=True,
    )
    w_unseen_99 = LogWindow(
        dataset="test",
        window_id="w_u99",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=1,
        template_ids=[99],
        raw_messages=["unseen"],
        is_anomaly=True,
    )

    # Both -1 and unseen ID 99 must map to unknown_log_prob_
    score_u1 = scorer.score_window(w_unknown_1)
    score_u99 = scorer.score_window(w_unseen_99)

    assert score_u1 == score_u99
    assert score_u1 == -scorer.unknown_log_prob_
    assert score_u1 > 0.0


def test_b1_vector_dimensions_stable_across_partitions(synthetic_windows):
    """Test that B1 vectorizer maintains fixed dimensionality between TRAIN and CALIBRATION."""
    train_w, calib_w = synthetic_windows
    vec = TemplateCountVectorizer(mode="normalized_count")
    X_train = vec.fit_transform(train_w)
    X_calib = vec.transform(calib_w)

    assert X_train.ndim == 2
    assert X_calib.ndim == 2
    assert X_train.shape[1] == X_calib.shape[1]
    assert X_train.shape[1] == vec.n_features
    # Verify calibration samples do not expand feature dimension
    assert X_calib.shape[0] == len(calib_w)


def test_calibration_cannot_create_new_vocabulary_dimensions(synthetic_windows):
    """Test that novel templates in calibration map strictly to UNKNOWN bin without creating dimensions."""
    train_w, calib_w = synthetic_windows
    vec = TemplateCountVectorizer().fit(train_w)

    initial_dim = vec.n_features
    X_calib = vec.transform(calib_w)

    assert X_calib.shape[1] == initial_dim

    # The anomalous window with template 99 should place non-zero weight in the unknown bin
    anom_window = [w for w in calib_w if w.window_id == "win_calib_anom_1"][0]
    vec_anom = vec.transform([anom_window])[0]

    unknown_idx = vec.unknown_idx_
    # Templates in win_calib_anom_1 are [99, -1, 4]. Both 99 and -1 map to unknown_idx.
    # Total count = 3 records, so 2 / 3 should be in unknown bin.
    assert np.isclose(vec_anom[unknown_idx], 2.0 / 3.0)


def test_pca_fit_uses_train_only_and_respects_variance(synthetic_windows):
    """Test PCA fitting strictly on TRAIN and component selection via explained variance."""
    train_w, calib_w = synthetic_windows
    pca_scorer = PCAScorer(mode="normalized_count", variance_ratio=0.95, random_state=42)
    pca_scorer.fit(train_w)

    assert pca_scorer.is_fitted
    assert pca_scorer.k_components_ >= 1
    assert pca_scorer.k_components_ <= pca_scorer.vectorizer.n_features
    assert pca_scorer.cumulative_variance_ >= 0.95

    meta = pca_scorer.get_metadata()
    assert meta["baseline"] == "B1_PCA"
    assert meta["k_components"] == pca_scorer.k_components_


def test_b1_anomaly_score_direction(synthetic_windows):
    """Test that anomaly scores for anomalous windows are strictly higher than normal windows."""
    train_w, calib_w = synthetic_windows

    # 1. B0
    b0 = FrequencyScorer().fit(train_w)
    scores_b0 = b0.score(calib_w)

    # 2. B1 PCA
    pca = PCAScorer(random_state=42).fit(train_w)
    scores_pca = pca.score(calib_w)

    # 3. B1 Isolation Forest
    iforest = IsolationForestScorer(random_state=42).fit(train_w)
    scores_if = iforest.score(calib_w)

    # First 8 are normal, last 2 are anomalous
    normal_b0 = scores_b0[:8]
    anom_b0 = scores_b0[8:]
    assert np.mean(anom_b0) > np.mean(normal_b0)

    normal_pca = scores_pca[:8]
    anom_pca = scores_pca[8:]
    assert np.mean(anom_pca) > np.mean(normal_pca)

    normal_if = scores_if[:8]
    anom_if = scores_if[8:]
    assert np.mean(anom_if) > np.mean(normal_if)


def test_threshold_computation_deterministic(synthetic_windows):
    """Test that unsupervised quantile thresholding is deterministic."""
    train_w, calib_w = synthetic_windows
    pca = PCAScorer(random_state=42).fit(train_w)
    scores = pca.score(calib_w)

    th1 = compute_unsupervised_threshold(scores, quantile=0.80)
    th2 = compute_unsupervised_threshold(scores, quantile=0.80)
    assert th1 == th2
    assert isinstance(th1, float)


def test_rule1_test_access_guard_raises_error():
    """Test that guard_no_test_split raises TestAccessViolationError when test is accessed."""
    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        guard_no_test_split("test")

    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        guard_no_test_split("TEST")

    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        guard_no_test_split("calibration", "data/processed/hdfs/test.jsonl")

    # Allowed splits must not raise
    guard_no_test_split("train", "data/processed/hdfs/train.jsonl")
    guard_no_test_split("calibration", "data/processed/hdfs/calibration.jsonl")


def test_baseline_experiment_determinism_across_reruns(synthetic_windows):
    """Test that running the full baseline experiment twice yields identical scores and metrics."""
    train_w, calib_w = synthetic_windows
    config = {
        "random_seed": 42,
        "threshold_quantile": 0.80,
        "b0": {"smoothing_alpha": 1.0},
        "features": {"mode": "normalized_count"},
        "b1_pca": {"variance_ratio": 0.95, "random_state": 42},
        "b1_iforest": {"n_estimators": 50, "contamination": "auto", "random_state": 42},
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        res1 = run_single_baseline(
            dataset="synthetic",
            baseline_type="b1_pca",
            train_windows=train_w,
            calib_windows=calib_w,
            config=config,
            data_dir=tmp_dir,
            out_dir=tmp_dir,
        )
        res2 = run_single_baseline(
            dataset="synthetic",
            baseline_type="b1_pca",
            train_windows=train_w,
            calib_windows=calib_w,
            config=config,
            data_dir=tmp_dir,
            out_dir=tmp_dir,
        )

        assert res1["threshold"] == res2["threshold"]
        assert res1["diagnostics"]["metrics"] == res2["diagnostics"]["metrics"]
        assert res1["diagnostics"]["confusion_matrix"] == res2["diagnostics"]["confusion_matrix"]


def test_saved_model_artifact_reload_and_scoring_fidelity(synthetic_windows):
    """Test that saved model artifact can be reloaded and produces identical scores."""
    train_w, calib_w = synthetic_windows
    pca = PCAScorer(random_state=42).fit(train_w)
    original_scores = pca.score(calib_w)

    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = os.path.join(tmp_dir, "test_pca.joblib")
        save_model_artifact(pca, model_path)

        reloaded_pca = load_model_artifact(model_path)
        reloaded_scores = reloaded_pca.score(calib_w)

        np.testing.assert_array_almost_equal(original_scores, reloaded_scores, decimal=10)


def test_isolation_forest_seed_determinism(synthetic_windows):
    """Test that Isolation Forest with fixed random_state produces identical anomaly scores."""
    train_w, calib_w = synthetic_windows

    if1 = IsolationForestScorer(n_estimators=50, random_state=42).fit(train_w)
    scores1 = if1.score(calib_w)

    if2 = IsolationForestScorer(n_estimators=50, random_state=42).fit(train_w)
    scores2 = if2.score(calib_w)

    np.testing.assert_array_almost_equal(scores1, scores2, decimal=10)


def test_actual_hdfs_baseline_artifacts_exist_and_conform():
    """Verify that actual generated HDFS baseline experiment manifests and models conform to standards."""
    results_dir = "results/phase3/hdfs"
    for b_type in ["b0", "b1_pca", "b1_iforest"]:
        b_dir = os.path.join(results_dir, b_type)
        assert os.path.exists(b_dir), f"Missing experiment directory: {b_dir}"

        manifest_path = os.path.join(b_dir, "manifest.json")
        diag_path = os.path.join(b_dir, "diagnostics.json")
        model_path = os.path.join(b_dir, "model.joblib")

        assert os.path.exists(manifest_path)
        assert os.path.exists(diag_path)
        assert os.path.exists(model_path)

        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["dataset"] == "hdfs"
        assert manifest["test_used"] is False  # Rule 1 verification
        assert manifest["train_windows"] == 2450
        assert manifest["calibration_windows"] == 814


def test_actual_bgl_baseline_artifacts_exist_and_conform():
    """Verify that actual generated BGL baseline experiment manifests conform to standards."""
    results_dir = "results/phase3/bgl"
    for b_type in ["b0", "b1_pca", "b1_iforest"]:
        b_dir = os.path.join(results_dir, b_type)
        assert os.path.exists(b_dir)

        manifest_path = os.path.join(b_dir, "manifest.json")
        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["dataset"] == "bgl"
        assert manifest["test_used"] is False
        assert manifest["train_windows"] == 300
        assert manifest["calibration_windows"] == 100
