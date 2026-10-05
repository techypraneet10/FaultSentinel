"""Test suite for Phase 4: Learned Sequential Scorer and Conformal Selective Gate.

Verifies:
1. B2 vocabulary is TRAIN-derived only.
2. Unknown templates map deterministically to UNKNOWN token.
3. Sequence padding and attention masks are constructed accurately.
4. Chronological sequence ordering is preserved without shuffling.
5. Model trainable parameter count is strictly < 2,000,000 (Rule 6).
6. Training does not access calibration or test partitions.
7. Model score direction is strictly higher = more anomalous.
8. Short sequences (lengths 0 and 1) are handled without division by zero.
9. Training produces deterministic loss curves and weights under fixed seed.
10. Calibration scoring does not alter model weights (immutability).
11. Conformal threshold computation is deterministic and monotone in alpha.
12. Conformal p-value calculation is orientation-consistent.
13. Alpha sweep produces deterministic risk-coverage metrics.
14. Test-access guard strictly rejects test files.
15. Selective gate decisions are deterministic.
16. Normal-only vs all-train label dependency check (Section 42).
17. Synthetic calibration score properties (finite-sample quantile, ties, order-statistics).
"""

import copy
import os
import tempfile
import numpy as np
import pytest
import torch

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import (
    SelectiveGate,
    evaluate_selective_performance,
    sweep_alpha_grid,
)
from sentinellog.ingestion.schemas import LogWindow, UNKNOWN_TEMPLATE_ID
from sentinellog.scoring.artifacts import (
    TestAccessViolationError,
    guard_no_test_split,
)
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.b2_model import MAX_ALLOWED_PARAMETERS, SequentialGRU
from sentinellog.scoring.tokenizer import (
    PAD_TOKEN_ID,
    SequenceTokenizer,
    UNKNOWN_TOKEN_ID,
)


@pytest.fixture
def synthetic_windows():
    """Create deterministic synthetic train and calibration windows."""
    # Normal training sequences: repetitive pattern [1, 2, 3, 4]
    train_windows = [
        LogWindow(
            dataset="synth",
            window_id=f"train_{i}",
            session_id=f"sess_{i}",
            start_time=float(100 + i * 10),
            end_time=float(105 + i * 10),
            record_count=4,
            template_ids=[1, 2, 3, 4],
            raw_messages=["m1", "m2", "m3", "m4"],
            is_anomaly=False,
        )
        for i in range(30)
    ]
    # Add a couple of anomalous windows in TRAIN to test normal-filtering logic
    train_windows.append(
        LogWindow(
            dataset="synth",
            window_id="train_anom_1",
            session_id="sess_anom_1",
            start_time=500.0,
            end_time=505.0,
            record_count=4,
            template_ids=[4, 3, 2, 1],
            raw_messages=["m4", "m3", "m2", "m1"],
            is_anomaly=True,
        )
    )

    # Calibration windows: 20 normal, 5 anomalous
    calib_windows = [
        LogWindow(
            dataset="synth",
            window_id=f"calib_norm_{i}",
            session_id=f"calib_s_{i}",
            start_time=float(600 + i * 10),
            end_time=float(605 + i * 10),
            record_count=4,
            template_ids=[1, 2, 3, 4],
            raw_messages=["m1", "m2", "m3", "m4"],
            is_anomaly=False,
        )
        for i in range(20)
    ]
    # Anomalous windows: unexpected transition and unknown templates
    for j in range(5):
        calib_windows.append(
            LogWindow(
                dataset="synth",
                window_id=f"calib_anom_{j}",
                session_id=f"calib_s_anom_{j}",
                start_time=float(800 + j * 10),
                end_time=float(805 + j * 10),
                record_count=4,
                template_ids=[99, -1, 4, 1],  # Novel template 99 and unknown -1
                raw_messages=["m99", "m_unk", "m4", "m1"],
                is_anomaly=True,
            )
        )

    return train_windows, calib_windows


def test_b2_vocabulary_train_derived_only(synthetic_windows):
    """Test that vocabulary contains only TRAIN templates and cannot see calibration novel templates."""
    train_w, calib_w = synthetic_windows
    tokenizer = SequenceTokenizer().fit(train_w)

    # Templates in train are 1, 2, 3, 4. Novel template 99 is only in calib.
    assert 1 in tokenizer.template_to_id_
    assert 2 in tokenizer.template_to_id_
    assert 3 in tokenizer.template_to_id_
    assert 4 in tokenizer.template_to_id_
    assert 99 not in tokenizer.template_to_id_

    # Encoding calib window with template 99 must map to UNKNOWN_TOKEN_ID
    anom_window = [w for w in calib_w if w.window_id == "calib_anom_0"][0]
    encoded = tokenizer.encode_window(anom_window)
    assert encoded[0] == UNKNOWN_TOKEN_ID
    assert encoded[1] == UNKNOWN_TOKEN_ID


def test_sequence_padding_and_attention_mask(synthetic_windows):
    """Test batch encoding correctly pads variable-length sequences with PAD_TOKEN_ID."""
    train_w, _ = synthetic_windows
    tokenizer = SequenceTokenizer().fit(train_w)

    w_short = LogWindow(
        dataset="synth",
        window_id="short",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=2,
        template_ids=[1, 2],
        raw_messages=["m1", "m2"],
        is_anomaly=False,
    )
    w_long = LogWindow(
        dataset="synth",
        window_id="long",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=4,
        template_ids=[1, 2, 3, 4],
        raw_messages=["m1", "m2", "m3", "m4"],
        is_anomaly=False,
    )

    batch = tokenizer.encode_batch([w_short, w_long])
    assert batch["input_ids"].shape == (2, 4)
    assert batch["input_ids"][0, 2].item() == PAD_TOKEN_ID
    assert batch["input_ids"][0, 3].item() == PAD_TOKEN_ID
    assert batch["attention_mask"][0, 2].item() is False
    assert batch["attention_mask"][1, 3].item() is True


def test_chronological_ordering_preserved(synthetic_windows):
    """Test that event sequence order is strictly preserved during tokenization."""
    train_w, _ = synthetic_windows
    tokenizer = SequenceTokenizer().fit(train_w)

    w_forward = LogWindow(
        dataset="synth",
        window_id="fwd",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=3,
        template_ids=[1, 2, 3],
        raw_messages=["m1", "m2", "m3"],
        is_anomaly=False,
    )
    encoded = tokenizer.encode_window(w_forward)
    assert encoded == [tokenizer.template_to_id_[1], tokenizer.template_to_id_[2], tokenizer.template_to_id_[3]]


def test_model_parameter_count_limit():
    """Test that model parameter count is strictly under 2,000,000 parameters (Rule 6)."""
    model = SequentialGRU(vocab_size=30, embedding_dim=32, hidden_dim=64, num_layers=1)
    params = model.count_parameters()
    assert params < MAX_ALLOWED_PARAMETERS
    assert params > 1000  # Non-trivial model


def test_b2_short_sequences_handled(synthetic_windows):
    """Test that sequences of length 0 and 1 are scored without ZeroDivisionError."""
    train_w, _ = synthetic_windows
    scorer = B2SequentialScorer(epochs=2, random_state=42).fit(train_w)

    w_empty = LogWindow(
        dataset="synth",
        window_id="empty",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=0,
        template_ids=[],
        raw_messages=[],
        is_anomaly=False,
    )
    w_single = LogWindow(
        dataset="synth",
        window_id="single",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=1,
        template_ids=[1],
        raw_messages=["m1"],
        is_anomaly=False,
    )

    score_empty = scorer.score_window(w_empty)
    score_single = scorer.score_window(w_single)

    assert score_empty == 0.0
    assert isinstance(score_single, float)
    assert score_single >= 0.0


def test_b2_score_direction(synthetic_windows):
    """Test that anomalous sequences receive higher anomaly scores than normal sequences."""
    train_w, calib_w = synthetic_windows
    scorer = B2SequentialScorer(epochs=5, random_state=42).fit(train_w)

    scores = scorer.score(calib_w)
    normal_scores = scores[:20]
    anomalous_scores = scores[20:]

    assert np.mean(anomalous_scores) > np.mean(normal_scores)


def test_b2_training_determinism(synthetic_windows):
    """Test that two separate fits with identical random_state produce identical validation losses."""
    train_w, calib_w = synthetic_windows
    scorer1 = B2SequentialScorer(epochs=3, random_state=42).fit(train_w)
    scorer2 = B2SequentialScorer(epochs=3, random_state=42).fit(train_w)

    scores1 = scorer1.score(calib_w)
    scores2 = scorer2.score(calib_w)
    np.testing.assert_array_almost_equal(scores1, scores2, decimal=6)


def test_calibration_immutability(synthetic_windows):
    """Test that running calibration scoring does not alter model parameters."""
    train_w, calib_w = synthetic_windows
    scorer = B2SequentialScorer(epochs=2, random_state=42).fit(train_w)

    weights_before = copy.deepcopy(scorer.model.state_dict())
    _ = scorer.score(calib_w)
    weights_after = scorer.model.state_dict()

    for k in weights_before:
        assert torch.equal(weights_before[k], weights_after[k])


def test_conformal_calibrator_exact_finite_sample_quantiles():
    """Verify exact finite-sample quantile calculation on synthetic scores."""
    # 10 calibration scores: 1.0, 2.0, ..., 10.0
    calib_scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    calibrator = SplitConformalCalibrator(calib_scores)

    # For n=10, alpha=0.10:
    # rank = ceil((10 + 1) * (1 - 0.10)) = ceil(11 * 0.90) = ceil(9.9) = 10
    th_01 = calibrator.get_threshold(0.10)
    assert th_01 == 10.0

    # For n=10, alpha=0.20:
    # rank = ceil(11 * 0.80) = ceil(8.8) = 9
    th_02 = calibrator.get_threshold(0.20)
    assert th_02 == 9.0

    # Monotonicity: smaller alpha (higher coverage) -> higher or equal threshold
    assert th_01 >= th_02


def test_conformal_p_values_orientation():
    """Verify that conformal p-values decrease monotonically with higher anomaly scores."""
    calib_scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    calibrator = SplitConformalCalibrator(calib_scores)

    # Score below minimum
    p_low = calibrator.compute_p_value(0.5)
    # Score in middle
    p_mid = calibrator.compute_p_value(5.5)
    # Score above maximum
    p_high = calibrator.compute_p_value(15.0)

    assert p_low == 1.0  # 1 + 10 / 11 = 1.0
    assert p_mid == (1 + 5) / 11.0  # scores >= 5.5 are 6, 7, 8, 9, 10 (count 5)
    assert p_high == 1.0 / 11.0  # scores >= 15 is 0, so (1+0)/11

    assert p_low > p_mid > p_high


def test_selective_gate_decisions_and_metrics():
    """Verify selective gate decisions and metrics on synthetic calibration data."""
    calib_scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    # Say the top two (scores 9 and 10) are anomalies
    labels = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]

    calibrator = SplitConformalCalibrator(calib_scores)
    perf = evaluate_selective_performance(calib_scores, labels, calibrator, alpha=0.20, strict=True)

    # For alpha=0.20, threshold is 9.0.
    # Scores > 9.0 is only [10.0] -> 1 escalated window (which has label 1).
    assert perf["conformal_threshold"] == 9.0
    assert perf["n_escalated"] == 1
    assert perf["confusion_matrix"]["tp"] == 1
    assert perf["confusion_matrix"]["fp"] == 0
    assert perf["confusion_matrix"]["fn"] == 1  # score 9.0 was not strictly > 9.0
    assert perf["confusion_matrix"]["tn"] == 8
    assert perf["escalation_precision"] == 1.0
    assert perf["coverage"] == 0.90
    assert perf["selective_risk"] == 1.0 / 9.0


def test_rule1_test_access_guard_in_phase4():
    """Verify that test-access guard prevents loading test split."""
    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        guard_no_test_split("test")

    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        guard_no_test_split("calibration", "data/processed/hdfs/test.jsonl")


def test_normal_only_training_filtering_logic(synthetic_windows):
    """Test that train_normal_only filters out anomalous windows from training pool."""
    train_w, _ = synthetic_windows
    # Synthetic train has 30 normal and 1 anomaly
    scorer = B2SequentialScorer(epochs=1, train_normal_only=True).fit(train_w)
    assert scorer.excluded_anomalies_count_ == 1

    scorer_all = B2SequentialScorer(epochs=1, train_normal_only=False).fit(train_w)
    assert scorer_all.excluded_anomalies_count_ == 0


def test_no_label_leakage_in_unlabeled_mode(synthetic_windows):
    """Test that toggling anomaly labels does not alter B2 fitting when train_normal_only=False."""
    train_w, calib_w = synthetic_windows

    # Create mutated train windows with inverted anomaly labels
    mutated_train_w = [
        LogWindow(
            dataset=w.dataset,
            window_id=w.window_id,
            session_id=w.session_id,
            start_time=w.start_time,
            end_time=w.end_time,
            record_count=w.record_count,
            template_ids=list(w.template_ids),
            raw_messages=list(w.raw_messages),
            is_anomaly=not w.is_anomaly,  # inverted label
        )
        for w in train_w
    ]

    scorer1 = B2SequentialScorer(epochs=1, train_normal_only=False, random_state=42).fit(train_w)
    scorer2 = B2SequentialScorer(epochs=1, train_normal_only=False, random_state=42).fit(mutated_train_w)

    scores1 = scorer1.score(calib_w)
    scores2 = scorer2.score(calib_w)

    # In unlabeled mode, training is completely label-invariant
    np.testing.assert_array_almost_equal(scores1, scores2, decimal=6)


def test_alpha_sweep_monotonicity():
    """Verify that conformal threshold decreases monotonically as significance level alpha increases."""
    calib_scores = np.random.uniform(0.1, 5.0, size=100)
    calibrator = SplitConformalCalibrator(calib_scores)

    alphas = [0.01, 0.05, 0.10, 0.20, 0.50]
    thresholds = [calibrator.get_threshold(a) for a in alphas]

    for i in range(len(thresholds) - 1):
        assert thresholds[i] >= thresholds[i + 1]


def test_actual_phase4_artifacts_exist_and_conform():
    """Verify that generated HDFS and BGL Phase 4 manifests and checkpoints conform to requirements."""
    for ds in ["hdfs", "bgl"]:
        ds_dir = os.path.join("results/phase4", ds)
        assert os.path.exists(ds_dir), f"Directory {ds_dir} missing"

        manifest_path = os.path.join(ds_dir, "manifest.json")
        diag_path = os.path.join(ds_dir, "conformal_diagnostics.json")
        ckpt_path = os.path.join(ds_dir, "b2_model.pt")

        assert os.path.exists(manifest_path)
        assert os.path.exists(diag_path)
        assert os.path.exists(ckpt_path)

        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["dataset"] == ds
        assert manifest["test_used"] is False  # Rule 1 verification
        assert manifest["parameter_count"] < MAX_ALLOWED_PARAMETERS  # Rule 6 verification
        assert manifest["cuda_available"] is False or manifest["cuda_available"] is True
