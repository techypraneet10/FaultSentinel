"""Comprehensive leakage, integrity, and determinism tests for Phase 2 data pipeline.

Verifies:
1. Drain3 parsing and explicit unknown template preservation.
2. HDFS session-based windowing and BGL fixed-size windowing.
3. Chronological splitting with zero ID or session leakage across partitions.
4. DataLeakageError properly triggered on chronological inversion or ID overlap.
5. Deterministic preprocessing across repeated executions.
6. JSON Lines serialization/deserialization fidelity.
"""

import json
from pathlib import Path
import tempfile
import pytest

from sentinellog.ingestion.hasher import compute_bytes_sha256, compute_sha256
from sentinellog.ingestion.parser import DrainParser
from sentinellog.ingestion.pipeline import (
    load_hdfs_labels,
    read_windows_jsonl,
    write_windows_jsonl,
)
from sentinellog.ingestion.schemas import (
    LogWindow,
    ParsedLogRecord,
    UNKNOWN_TEMPLATE_ID,
    UNKNOWN_TEMPLATE_STR,
)
from sentinellog.ingestion.splitter import (
    DataLeakageError,
    chronological_split,
    verify_partition_integrity,
)
from sentinellog.ingestion.windowing import (
    build_bgl_fixed_windows,
    build_hdfs_session_windows,
)


# ---------------------------------------------------------------------------
# 1. Drain3 Parsing & Unknown Template Handling Tests
# ---------------------------------------------------------------------------

def test_hdfs_parser_valid_line():
    parser = DrainParser(dataset="hdfs", sim_th=0.5, depth=4)
    line = "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.19.102:54106 dest: /10.250.19.102:50010"
    rec = parser.parse_line(line, 1)

    assert rec.dataset == "hdfs"
    assert rec.line_number == 1
    assert rec.session_id == "blk_-1608999687919862906"
    assert rec.log_level == "INFO"
    assert rec.component == "dfs.DataNode$DataXceiver"
    assert rec.timestamp is not None
    assert rec.template_id != UNKNOWN_TEMPLATE_ID
    assert rec.template != UNKNOWN_TEMPLATE_STR
    assert "<*>" in rec.template  # Verified masking applied


def test_bgl_parser_valid_line():
    parser = DrainParser(dataset="bgl", sim_th=0.5, depth=4)
    normal_line = "- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected"
    anomaly_line = "FATAL 1117838580 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.43.00.000000 R02-M1-N0-C:J12-U11 RAS KERNEL FATAL memory parity error"

    rec_normal = parser.parse_line(normal_line, 1)
    rec_anomaly = parser.parse_line(anomaly_line, 2)

    assert rec_normal.dataset == "bgl"
    assert rec_normal.is_anomaly is False
    assert rec_normal.timestamp == 1117838570.0
    assert rec_normal.template_id != UNKNOWN_TEMPLATE_ID

    assert rec_anomaly.dataset == "bgl"
    assert rec_anomaly.is_anomaly is True
    assert rec_anomaly.timestamp == 1117838580.0


def test_unknown_template_explicit_preservation():
    """Verify that malformed or unparseable lines are not dropped and are explicitly tagged UNKNOWN."""
    parser = DrainParser(dataset="hdfs")
    malformed_line = "THIS IS NOT A VALID HDFS LOG LINE"
    rec = parser.parse_line(malformed_line, 99)

    assert rec.template_id == UNKNOWN_TEMPLATE_ID
    assert rec.template == UNKNOWN_TEMPLATE_STR
    assert rec.raw_message == malformed_line
    assert parser.get_stats()["unknown_records"] == 1


# ---------------------------------------------------------------------------
# 2. Window Construction Tests
# ---------------------------------------------------------------------------

def test_hdfs_session_window_construction():
    """Verify session grouping by block ID, ordering, and label mapping."""
    labels_map = {
        "blk_001": False,
        "blk_002": True,
    }
    records = [
        ParsedLogRecord("hdfs", 1, 100.0, "t1", "blk_001", "INFO", "comp", "msg 1", "tmpl 1", 1, None),
        ParsedLogRecord("hdfs", 2, 105.0, "t2", "blk_002", "INFO", "comp", "msg 2", "tmpl 1", 1, None),
        ParsedLogRecord("hdfs", 3, 110.0, "t3", "blk_001", "INFO", "comp", "msg 3", "tmpl 2", 2, None),
    ]

    windows = build_hdfs_session_windows(iter(records), labels_map)

    assert len(windows) == 2
    # blk_001 started at 100.0, blk_002 started at 105.0
    w1, w2 = windows[0], windows[1]

    assert w1.session_id == "blk_001"
    assert w1.record_count == 2
    assert w1.template_ids == [1, 2]
    assert w1.start_time == 100.0
    assert w1.end_time == 110.0
    assert w1.is_anomaly is False

    assert w2.session_id == "blk_002"
    assert w2.record_count == 1
    assert w2.is_anomaly is True


def test_bgl_fixed_window_construction():
    """Verify fixed-size chunking and any-anomaly window labeling."""
    records = [
        ParsedLogRecord("bgl", 1, 10.0, "t1", None, "INFO", "comp", "msg 1", "tmpl 1", 1, False),
        ParsedLogRecord("bgl", 2, 20.0, "t2", None, "INFO", "comp", "msg 2", "tmpl 1", 1, False),
        ParsedLogRecord("bgl", 3, 30.0, "t3", None, "FATAL", "comp", "msg 3", "tmpl 2", 2, True),
        ParsedLogRecord("bgl", 4, 40.0, "t4", None, "INFO", "comp", "msg 4", "tmpl 1", 1, False),
        ParsedLogRecord("bgl", 5, 50.0, "t5", None, "INFO", "comp", "msg 5", "tmpl 1", 1, False),
    ]

    windows = build_bgl_fixed_windows(iter(records), window_size=2, min_window_size=1)

    assert len(windows) == 3
    # Window 0: records 1, 2 (both normal -> window is normal)
    assert windows[0].record_count == 2
    assert windows[0].is_anomaly is False

    # Window 1: records 3, 4 (record 3 is anomaly -> window is anomaly)
    assert windows[1].record_count == 2
    assert windows[1].is_anomaly is True

    # Window 2: record 5 (partial window preserved deterministically)
    assert windows[2].record_count == 1
    assert windows[2].is_anomaly is False


# ---------------------------------------------------------------------------
# 3. Chronological Splitting & Leakage Verification Tests
# ---------------------------------------------------------------------------

def test_chronological_split_strict_isolation():
    """Verify 60/20/20 partition boundary ordering and disjoint IDs."""
    windows = [
        LogWindow("hdfs", f"w_{i:03d}", f"blk_{i:03d}", float(i * 10), float(i * 10 + 5), 1, [1], ["m"], False)
        for i in range(10)
    ]

    train, calib, test = chronological_split(windows, 0.6, 0.2, 0.2)

    assert len(train) == 6
    assert len(calib) == 2
    assert len(test) == 2

    # Verify ID disjointness
    train_ids = {w.window_id for w in train}
    calib_ids = {w.window_id for w in calib}
    test_ids = {w.window_id for w in test}

    assert train_ids.isdisjoint(calib_ids)
    assert train_ids.isdisjoint(test_ids)
    assert calib_ids.isdisjoint(test_ids)

    # Verify strict temporal boundaries
    assert max(w.start_time for w in train) <= min(w.start_time for w in calib)
    assert max(w.start_time for w in calib) <= min(w.start_time for w in test)


def test_leakage_detector_catches_session_overlap():
    """Verify that DataLeakageError is raised if the same session appears in two splits."""
    w1 = LogWindow("hdfs", "w1", "blk_SAME", 10.0, 15.0, 1, [1], ["m"], False)
    w2 = LogWindow("hdfs", "w2", "blk_OTHER", 20.0, 25.0, 1, [1], ["m"], False)
    w3 = LogWindow("hdfs", "w3", "blk_SAME", 30.0, 35.0, 1, [1], ["m"], False)

    with pytest.raises(DataLeakageError, match="Session ID overlap"):
        verify_partition_integrity([w1], [w2], [w3])


def test_leakage_detector_catches_chronological_inversion():
    """Verify that DataLeakageError is raised if train has events from the future."""
    w1 = LogWindow("hdfs", "w1", "blk_1", 100.0, 105.0, 1, [1], ["m"], False)  # Future event in train
    w2 = LogWindow("hdfs", "w2", "blk_2", 20.0, 25.0, 1, [1], ["m"], False)   # Earlier event in calib

    with pytest.raises(DataLeakageError, match="Chronological inversion"):
        verify_partition_integrity([w1], [w2], [])


# ---------------------------------------------------------------------------
# 4. Determinism & Serialization Tests
# ---------------------------------------------------------------------------

def test_jsonl_serialization_fidelity():
    """Verify round-trip persistence of LogWindow objects without data loss."""
    original_window = LogWindow(
        dataset="hdfs",
        window_id="hdfs_session_blk_123",
        session_id="blk_123",
        start_time=1234567.89,
        end_time=1234599.99,
        record_count=3,
        template_ids=[1, 2, -1],
        raw_messages=["msg1", "msg2", "msg3"],
        is_anomaly=True,
        metadata={"has_unknown_template": True},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.jsonl"
        write_windows_jsonl([original_window], file_path)

        loaded_windows = read_windows_jsonl(file_path)
        assert len(loaded_windows) == 1
        loaded = loaded_windows[0]

        assert loaded.window_id == original_window.window_id
        assert loaded.session_id == original_window.session_id
        assert loaded.start_time == original_window.start_time
        assert loaded.template_ids == original_window.template_ids
        assert loaded.is_anomaly == original_window.is_anomaly
        assert loaded.metadata == original_window.metadata


def test_pipeline_determinism_on_synthetic_stream():
    """Verify that running parsing and windowing on identical input produces byte-identical JSONL output."""
    raw_lines = [
        "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_100 src: /10.0.0.1:1 dest: /10.0.0.2:2",
        "081109 203519 144 INFO dfs.DataNode$DataXceiver: Received block blk_100 of size 100",
        "081109 203525 145 INFO dfs.DataNode$DataXceiver: Receiving block blk_200 src: /10.0.0.1:1 dest: /10.0.0.2:2",
    ]
    labels_map = {"blk_100": False, "blk_200": True}

    def run_subpipe():
        parser = DrainParser(dataset="hdfs")
        recs = [parser.parse_line(l, idx) for idx, l in enumerate(raw_lines, 1)]
        return build_hdfs_session_windows(iter(recs), labels_map)

    windows1 = run_subpipe()
    windows2 = run_subpipe()

    assert len(windows1) == len(windows2)
    for w1, w2 in zip(windows1, windows2):
        assert w1.to_dict() == w2.to_dict()


# ---------------------------------------------------------------------------
# 5. Processed Artifact Integrity & Leakage Verification Tests
# ---------------------------------------------------------------------------

def test_actual_hdfs_processed_artifacts_integrity():
    """Verify structural integrity and zero leakage on generated HDFS artifacts."""
    hdfs_proc = Path("data/processed/hdfs")
    assert (hdfs_proc / "train.jsonl").exists(), "HDFS train.jsonl missing"
    assert (hdfs_proc / "calibration.jsonl").exists(), "HDFS calibration.jsonl missing"
    assert (hdfs_proc / "test.jsonl").exists(), "HDFS test.jsonl missing"
    assert (hdfs_proc / "manifest.json").exists(), "HDFS manifest.json missing"
    assert (hdfs_proc / "data_quality_report.json").exists(), "HDFS data_quality_report.json missing"

    train = read_windows_jsonl(hdfs_proc / "train.jsonl")
    calib = read_windows_jsonl(hdfs_proc / "calibration.jsonl")
    test = read_windows_jsonl(hdfs_proc / "test.jsonl")

    assert len(train) == 2450
    assert len(calib) == 814
    assert len(test) == 823
    assert len(train) + len(calib) + len(test) == 4087

    # Verify partition integrity: zero session/window ID overlap, strict chronological boundaries
    verify_partition_integrity(train, calib, test, require_strict_timestamp_inequality=True)


def test_actual_bgl_processed_artifacts_integrity():
    """Verify structural integrity and zero leakage on generated BGL artifacts."""
    bgl_proc = Path("data/processed/bgl")
    assert (bgl_proc / "train.jsonl").exists(), "BGL train.jsonl missing"
    assert (bgl_proc / "calibration.jsonl").exists(), "BGL calibration.jsonl missing"
    assert (bgl_proc / "test.jsonl").exists(), "BGL test.jsonl missing"
    assert (bgl_proc / "manifest.json").exists(), "BGL manifest.json missing"
    assert (bgl_proc / "data_quality_report.json").exists(), "BGL data_quality_report.json missing"

    train = read_windows_jsonl(bgl_proc / "train.jsonl")
    calib = read_windows_jsonl(bgl_proc / "calibration.jsonl")
    test = read_windows_jsonl(bgl_proc / "test.jsonl")

    assert len(train) == 300
    assert len(calib) == 100
    assert len(test) == 100
    assert len(train) + len(calib) + len(test) == 500

    # Verify partition integrity: zero window ID overlap, strict chronological boundaries
    verify_partition_integrity(train, calib, test, require_strict_timestamp_inequality=True)


def test_frozen_vocabulary_prevents_leakage():
    """Regression test: calibration and test novel templates must map to UNKNOWN (-1) without altering train clusters."""
    parser = DrainParser(dataset="hdfs", sim_th=0.5, depth=4)

    # 1. Training Phase: learn templates T1 and T2
    t1_line = "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-100 src: /10.0.0.1:1 dest: /10.0.0.2:2"
    t2_line = "081109 203519 144 INFO dfs.DataNode$DataXceiver: Received block blk_-100 of size 100"

    rec1 = parser.parse_hdfs_line(t1_line, 1)
    rec2 = parser.parse_hdfs_line(t2_line, 2)

    assert rec1.template_id != UNKNOWN_TEMPLATE_ID
    assert rec2.template_id != UNKNOWN_TEMPLATE_ID
    initial_clusters = len(parser.miner.drain.id_to_cluster)
    assert initial_clusters >= 2

    # 2. Freeze Vocabulary: simulate transition to calibration/test
    parser.freeze()
    assert parser.is_frozen is True

    # 3. Calibration Phase:
    # A known template must match its trained cluster ID
    t1_calib = "081109 203530 145 INFO dfs.DataNode$DataXceiver: Receiving block blk_-200 src: /10.0.0.3:3 dest: /10.0.0.4:4"
    rec1_calib = parser.parse_hdfs_line(t1_calib, 3)
    assert rec1_calib.template_id == rec1.template_id

    # A novel calibration-only template MUST map to UNKNOWN (-1)
    novel_calib_line = "081109 203535 146 ERROR dfs.DataNode$DataXceiver: Transmission channel disconnected unexpectedly"
    rec_novel_calib = parser.parse_hdfs_line(novel_calib_line, 4)
    assert rec_novel_calib.template_id == UNKNOWN_TEMPLATE_ID
    assert rec_novel_calib.template == UNKNOWN_TEMPLATE_STR

    # 4. Test Phase:
    # A novel test-only template MUST map to UNKNOWN (-1)
    novel_test_line = "081109 203540 147 FATAL dfs.DataNode$DataXceiver: Core filesystem corrupted on block device"
    rec_novel_test = parser.parse_hdfs_line(novel_test_line, 5)
    assert rec_novel_test.template_id == UNKNOWN_TEMPLATE_ID
    assert rec_novel_test.template == UNKNOWN_TEMPLATE_STR

    # 5. Verify that Drain3 cluster count did NOT grow during frozen parsing
    final_clusters = len(parser.miner.drain.id_to_cluster)
    assert final_clusters == initial_clusters, "Template vocabulary leaked from calibration/test into Drain3 clusters!"


def test_full_pipeline_rerun_determinism():
    """Verify that rerunning the pipeline produces identical window IDs, counts, and labels."""
    from sentinellog.ingestion.pipeline import process_hdfs

    config = {
        "raw_dir": "data/raw",
        "parser": {"sim_th": 0.5, "depth": 4, "max_children": 100},
        "subsample": {"hdfs_max_records": 5000},
        "split": {"train_ratio": 0.60, "calib_ratio": 0.20, "test_ratio": 0.20},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_proc = Path(tmpdir)
        res1 = process_hdfs(config, Path("data/raw"), tmp_proc / "run1")
        res2 = process_hdfs(config, Path("data/raw"), tmp_proc / "run2")

        assert res1["total_windows"] == res2["total_windows"]
        assert res1["train"] == res2["train"]
        assert res1["calibration"] == res2["calibration"]
        assert res1["test"] == res2["test"]

        # Check identical window IDs in train split
        train1 = read_windows_jsonl(tmp_proc / "run1" / "hdfs" / "train.jsonl")
        train2 = read_windows_jsonl(tmp_proc / "run2" / "hdfs" / "train.jsonl")

        assert [w.window_id for w in train1] == [w.window_id for w in train2]
        assert [w.is_anomaly for w in train1] == [w.is_anomaly for w in train2]
        assert [w.template_ids for w in train1] == [w.template_ids for w in train2]
