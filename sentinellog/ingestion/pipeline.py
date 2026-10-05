"""End-to-end data pipeline orchestrator for SentinelLog.

Handles dataset validation, Drain3 parsing, window generation, chronological
splitting, artifact persistence (.jsonl format), and quality reporting.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import yaml

from sentinellog.ingestion.downloader import acquire_bgl, acquire_hdfs
from sentinellog.ingestion.hasher import compute_sha256, get_file_metadata
from sentinellog.ingestion.parser import DrainParser
from sentinellog.ingestion.schemas import (
    DataQualityReport,
    DatasetManifest,
    LogWindow,
)
from sentinellog.ingestion.splitter import (
    chronological_split,
    get_split_summary,
    verify_partition_integrity,
)
from sentinellog.ingestion.windowing import (
    build_bgl_fixed_windows,
    build_hdfs_session_windows,
)


def load_hdfs_labels(label_path: Path) -> Dict[str, bool]:
    """Load HDFS block ground truth labels from anomaly_label.csv.

    CSV header: BlockId,Label
    Label values: 'Normal' -> False, 'Anomaly' -> True
    """
    labels: Dict[str, bool] = {}
    if not label_path.exists():
        raise FileNotFoundError(f"HDFS anomaly label file not found: {label_path}")

    with open(label_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line or (idx == 0 and "BlockId" in line):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                block_id = parts[0].strip()
                label_str = parts[1].strip()
                labels[block_id] = (label_str.lower() == "anomaly")

    return labels


def write_windows_jsonl(windows: List[LogWindow], output_path: Path) -> None:
    """Serialize a list of LogWindow dataclasses to JSON Lines deterministically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for w in windows:
            f.write(json.dumps(w.to_dict(), ensure_ascii=False) + "\n")


def read_windows_jsonl(input_path: Path) -> List[LogWindow]:
    """Read a JSON Lines file into a list of LogWindow instances."""
    windows: List[LogWindow] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                windows.append(LogWindow.from_dict(data))
    return windows


def run_pipeline(config_path: Path) -> Dict[str, Any]:
    """Execute the data pipeline according to the given configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    results: Dict[str, Any] = {}
    datasets = config.get("datasets", ["hdfs", "bgl"])
    raw_root = Path(config.get("raw_dir", "data/raw"))
    proc_root = Path(config.get("processed_dir", "data/processed"))

    for ds in datasets:
        ds = ds.lower()
        if ds == "hdfs":
            res = process_hdfs(config, raw_root, proc_root)
            results["hdfs"] = res
        elif ds == "bgl":
            res = process_bgl(config, raw_root, proc_root)
            results["bgl"] = res
        else:
            raise ValueError(f"Unknown dataset configured: {ds}")

    return results


def process_hdfs(
    config: Dict[str, Any],
    raw_root: Path,
    proc_root: Path,
) -> Dict[str, Any]:
    """Process HDFS logs into session windows and chronological splits with frozen vocabulary."""
    hdfs_raw = raw_root / "hdfs"
    log_file = hdfs_raw / "HDFS.log"
    label_file = hdfs_raw / "anomaly_label.csv"

    # Acquire if missing and auto_download is enabled
    if not (log_file.exists() and label_file.exists()):
        if config.get("auto_download", False):
            acquire_hdfs(raw_root)
        else:
            raise FileNotFoundError(
                f"HDFS raw files not found at {hdfs_raw}. Set auto_download: true or run downloader."
            )

    labels_map = load_hdfs_labels(label_file)
    parser_cfg = config.get("parser", {})
    parser = DrainParser(
        dataset="hdfs",
        sim_th=parser_cfg.get("sim_th", 0.5),
        depth=parser_cfg.get("depth", 4),
        max_children=parser_cfg.get("max_children", 100),
    )

    max_records = config.get("subsample", {}).get("hdfs_max_records", None)

    # 1. First pass: Read raw lines and group into raw sessions by block ID
    from collections import defaultdict
    raw_sessions = defaultdict(list)
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            if max_records and idx > max_records:
                break
            line_str = line.strip()
            if not line_str:
                continue
            block_id = DrainParser._extract_hdfs_block_id(line_str)
            if block_id:
                raw_sessions[block_id].append((idx, line_str))

    # 2. Extract chronological ordering keys for each session
    session_metadata = []
    for block_id, lines in raw_sessions.items():
        # First record timestamp
        first_line_num, first_line_str = lines[0]
        match = re.match(r"^(\d{6})\s+(\d{6})", first_line_str)
        t_start = (
            DrainParser._parse_hdfs_timestamp(match.group(1), match.group(2))
            if match
            else None
        )
        session_metadata.append({
            "block_id": block_id,
            "start_time": t_start if t_start is not None else float("inf"),
            "first_line": first_line_num,
            "lines": lines,
        })

    # Sort sessions chronologically with deterministic secondary/tertiary keys
    session_metadata.sort(key=lambda s: (s["start_time"], s["first_line"], s["block_id"]))

    # 3. Create dummy/stub windows to determine chronological split boundaries
    stub_windows = [
        LogWindow(
            dataset="hdfs",
            window_id=f"hdfs_session_{s['block_id']}",
            session_id=s["block_id"],
            start_time=s["start_time"],
            end_time=s["start_time"],
            record_count=len(s["lines"]),
            template_ids=[],
            raw_messages=[],
            is_anomaly=labels_map.get(s["block_id"], False),
        )
        for s in session_metadata
    ]

    split_cfg = config.get("split", {})
    train_stubs, calib_stubs, test_stubs = chronological_split(
        stub_windows,
        train_ratio=split_cfg.get("train_ratio", 0.60),
        calib_ratio=split_cfg.get("calib_ratio", 0.20),
        test_ratio=split_cfg.get("test_ratio", 0.20),
        snap_to_timestamp_boundary=True,
    )

    n_train = len(train_stubs)
    n_calib = len(calib_stubs)

    train_sess_meta = session_metadata[:n_train]
    calib_sess_meta = session_metadata[n_train : n_train + n_calib]
    test_sess_meta = session_metadata[n_train + n_calib :]

    # 4. Phase 1 Fitting: Fit Drain3 ONLY on TRAIN sessions
    train_records = []
    for s in train_sess_meta:
        for idx, line_str in s["lines"]:
            train_records.append(parser.parse_hdfs_line(line_str, idx))

    # 5. Phase 2 Freezing: Freeze template vocabulary before CALIBRATION & TEST
    parser.freeze()

    calib_records = []
    for s in calib_sess_meta:
        for idx, line_str in s["lines"]:
            calib_records.append(parser.parse_hdfs_line(line_str, idx))

    test_records = []
    for s in test_sess_meta:
        for idx, line_str in s["lines"]:
            test_records.append(parser.parse_hdfs_line(line_str, idx))

    # 6. Build actual session windows from partition-parsed records
    train = build_hdfs_session_windows(iter(train_records), labels_map)
    calib = build_hdfs_session_windows(iter(calib_records), labels_map)
    test = build_hdfs_session_windows(iter(test_records), labels_map)
    windows = train + calib + test

    # Verify partition integrity on the realized windows
    verify_partition_integrity(train, calib, test, require_strict_timestamp_inequality=True)

    # Persistence
    ds_proc_dir = proc_root / "hdfs"
    train_path = ds_proc_dir / "train.jsonl"
    calib_path = ds_proc_dir / "calibration.jsonl"
    test_path = ds_proc_dir / "test.jsonl"

    write_windows_jsonl(train, train_path)
    write_windows_jsonl(calib, calib_path)
    write_windows_jsonl(test, test_path)

    # Quality Report & Manifest
    parser_stats = parser.get_stats()
    raw_meta = get_file_metadata(log_file)
    split_summary = get_split_summary(train, calib, test)

    report = DataQualityReport(
        dataset_name="hdfs",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_file_count=2,
        raw_bytes=raw_meta["size_bytes"],
        raw_sha256=raw_meta["sha256"],
        total_raw_records=parser_stats["total_records"],
        successfully_parsed_records=parser_stats["parsed_records"],
        unknown_template_records=parser_stats["unknown_records"],
        unique_template_count=parser_stats["unique_templates"],
        total_windows=len(windows),
        train_windows=len(train),
        calibration_windows=len(calib),
        test_windows=len(test),
        anomalous_windows=sum(1 for w in windows if w.is_anomaly),
        normal_windows=sum(1 for w in windows if not w.is_anomaly),
        missing_timestamps_count=sum(1 for w in windows if w.start_time is None),
        duplicate_window_ids_count=len(windows) - len({w.window_id for w in windows}),
        leakage_check_passed=True,
        details={
            "split_summary": split_summary,
            "max_records_applied": max_records,
            "label_file_sha256": compute_sha256(label_file),
            "vocabulary_frozen_on_train": True,
            "train_unique_templates": parser_stats["unique_templates"],
        },
    )

    manifest = DatasetManifest(
        dataset_name="hdfs",
        source_url="https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1",
        acquisition_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_filename=log_file.name,
        raw_file_size_bytes=raw_meta["size_bytes"],
        raw_sha256=raw_meta["sha256"],
        pipeline_version="0.2.1-phase2-freeze",
        parser_config_version="drain3-v1-sim0.5-depth4-frozen",
        windowing_config={"type": "session", "key": "block_id"},
        split_config=split_cfg,
        counts={
            "total_windows": len(windows),
            "train": len(train),
            "calibration": len(calib),
            "test": len(test),
        },
        notes="HDFS session-based windowing with train-only vocabulary fitting and frozen calib/test matching.",
    )

    with open(ds_proc_dir / "data_quality_report.json", "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    with open(ds_proc_dir / "manifest.json", "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)

    return {
        "dataset": "hdfs",
        "total_windows": len(windows),
        "train": len(train),
        "calibration": len(calib),
        "test": len(test),
        "report_path": str(ds_proc_dir / "data_quality_report.json"),
    }


def process_bgl(
    config: Dict[str, Any],
    raw_root: Path,
    proc_root: Path,
) -> Dict[str, Any]:
    """Process BGL logs into fixed-size windows and chronological splits with frozen vocabulary."""
    bgl_raw = raw_root / "bgl"
    log_file = bgl_raw / "BGL.log"

    if not log_file.exists():
        if config.get("auto_download", False):
            acquire_bgl(raw_root)
        else:
            raise FileNotFoundError(
                f"BGL raw file not found at {log_file}. Set auto_download: true or run downloader."
            )

    parser_cfg = config.get("parser", {})
    parser = DrainParser(
        dataset="bgl",
        sim_th=parser_cfg.get("sim_th", 0.5),
        depth=parser_cfg.get("depth", 4),
        max_children=parser_cfg.get("max_children", 100),
    )

    max_records = config.get("subsample", {}).get("bgl_max_records", None)
    window_size = config.get("windowing", {}).get("bgl_window_size", 100)

    # 1. Read raw lines
    raw_lines = []
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            if max_records and idx > max_records:
                break
            line_str = line.strip()
            if line_str:
                raw_lines.append((idx, line_str))

    # 2. Chunk into raw batches for fixed-size windowing
    raw_batches = [
        raw_lines[i : i + window_size]
        for i in range(0, len(raw_lines), window_size)
    ]

    # 3. Create stub windows for split determination
    stub_windows = []
    for idx, batch in enumerate(raw_batches):
        tokens_first = batch[0][1].split(maxsplit=2)
        start_ts = float(tokens_first[1]) if len(tokens_first) >= 2 else float("inf")
        stub_windows.append(
            LogWindow(
                dataset="bgl",
                window_id=f"bgl_window_{idx:07d}",
                session_id=None,
                start_time=start_ts,
                end_time=start_ts,
                record_count=len(batch),
                template_ids=[],
                raw_messages=[],
                is_anomaly=False,
            )
        )

    split_cfg = config.get("split", {})
    train_stubs, calib_stubs, test_stubs = chronological_split(
        stub_windows,
        train_ratio=split_cfg.get("train_ratio", 0.60),
        calib_ratio=split_cfg.get("calib_ratio", 0.20),
        test_ratio=split_cfg.get("test_ratio", 0.20),
        snap_to_timestamp_boundary=True,
    )

    n_train = len(train_stubs)
    n_calib = len(calib_stubs)

    train_batches = raw_batches[:n_train]
    calib_batches = raw_batches[n_train : n_train + n_calib]
    test_batches = raw_batches[n_train + n_calib :]

    # 4. Phase 1 Fitting: Fit Drain3 ONLY on TRAIN windows
    train_records = []
    for batch in train_batches:
        for idx, line_str in batch:
            train_records.append(parser.parse_bgl_line(line_str, idx))

    # 5. Phase 2 Freezing: Freeze vocabulary before CALIBRATION & TEST
    parser.freeze()

    calib_records = []
    for batch in calib_batches:
        for idx, line_str in batch:
            calib_records.append(parser.parse_bgl_line(line_str, idx))

    test_records = []
    for batch in test_batches:
        for idx, line_str in batch:
            test_records.append(parser.parse_bgl_line(line_str, idx))

    # 6. Build fixed windows from partition-parsed records
    train = build_bgl_fixed_windows(iter(train_records), window_size=window_size)
    calib = build_bgl_fixed_windows(iter(calib_records), window_size=window_size)
    test = build_bgl_fixed_windows(iter(test_records), window_size=window_size)

    # Renumber window IDs monotonically
    for idx, w in enumerate(train):
        w.window_id = f"bgl_window_{idx:07d}"
    for idx, w in enumerate(calib, start=len(train)):
        w.window_id = f"bgl_window_{idx:07d}"
    for idx, w in enumerate(test, start=len(train) + len(calib)):
        w.window_id = f"bgl_window_{idx:07d}"

    windows = train + calib + test

    # Verify partition integrity
    verify_partition_integrity(train, calib, test, require_strict_timestamp_inequality=True)

    # Persistence
    ds_proc_dir = proc_root / "bgl"
    train_path = ds_proc_dir / "train.jsonl"
    calib_path = ds_proc_dir / "calibration.jsonl"
    test_path = ds_proc_dir / "test.jsonl"

    write_windows_jsonl(train, train_path)
    write_windows_jsonl(calib, calib_path)
    write_windows_jsonl(test, test_path)

    # Quality Report & Manifest
    parser_stats = parser.get_stats()
    raw_meta = get_file_metadata(log_file)
    split_summary = get_split_summary(train, calib, test)

    report = DataQualityReport(
        dataset_name="bgl",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_file_count=1,
        raw_bytes=raw_meta["size_bytes"],
        raw_sha256=raw_meta["sha256"],
        total_raw_records=parser_stats["total_records"],
        successfully_parsed_records=parser_stats["parsed_records"],
        unknown_template_records=parser_stats["unknown_records"],
        unique_template_count=parser_stats["unique_templates"],
        total_windows=len(windows),
        train_windows=len(train),
        calibration_windows=len(calib),
        test_windows=len(test),
        anomalous_windows=sum(1 for w in windows if w.is_anomaly),
        normal_windows=sum(1 for w in windows if not w.is_anomaly),
        missing_timestamps_count=sum(1 for w in windows if w.start_time is None),
        duplicate_window_ids_count=len(windows) - len({w.window_id for w in windows}),
        leakage_check_passed=True,
        details={
            "split_summary": split_summary,
            "window_size": window_size,
            "max_records_applied": max_records,
        },
    )

    manifest = DatasetManifest(
        dataset_name="bgl",
        source_url="https://zenodo.org/records/8196385/files/BGL.zip?download=1",
        acquisition_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_filename=log_file.name,
        raw_file_size_bytes=raw_meta["size_bytes"],
        raw_sha256=raw_meta["sha256"],
        pipeline_version="0.2.0-phase2",
        parser_config_version="drain3-v1-sim0.5-depth4",
        windowing_config={"type": "fixed", "window_size": window_size},
        split_config=split_cfg,
        counts={
            "total_windows": len(windows),
            "train": len(train),
            "calibration": len(calib),
            "test": len(test),
        },
        notes="BGL fixed-size windowing (W=100) with chronological 60/20/20 partition.",
    )

    with open(ds_proc_dir / "data_quality_report.json", "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    with open(ds_proc_dir / "manifest.json", "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)

    return {
        "dataset": "bgl",
        "total_windows": len(windows),
        "train": len(train),
        "calibration": len(calib),
        "test": len(test),
        "report_path": str(ds_proc_dir / "data_quality_report.json"),
    }


def main():
    """CLI entrypoint for running the Phase 2 pipeline."""
    parser = argparse.ArgumentParser(description="SentinelLog Phase 2 Data Pipeline")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/data_pipeline.yaml",
        help="Path to pipeline configuration YAML file",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {cfg_path}")

    print(f"Executing SentinelLog Data Pipeline with configuration: {cfg_path}")
    results = run_pipeline(cfg_path)
    for ds_name, res in results.items():
        print(f"[{ds_name.upper()}] Processed {res['total_windows']} windows: "
              f"Train={res['train']}, Calib={res['calibration']}, Test={res['test']}. "
              f"Report: {res['report_path']}")


if __name__ == "__main__":
    main()
