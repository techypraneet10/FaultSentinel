"""Window construction logic for SentinelLog.

Implements:
1. Session-based windows for HDFS (grouped by BlockId).
2. Fixed-size windows for BGL (sequential chronological grouping).
"""

from collections import defaultdict
from typing import Dict, Iterator, List, Optional

from sentinellog.ingestion.schemas import LogWindow, ParsedLogRecord


def build_hdfs_session_windows(
    records: Iterator[ParsedLogRecord],
    labels_map: Dict[str, bool],
) -> List[LogWindow]:
    """Group HDFS parsed records into session windows by block ID.

    Maintains internal chronological order for each session and orders sessions
    chronologically by start time (tie-broken by block ID for strict determinism).

    Args:
        records: Stream/iterable of parsed HDFS log records.
        labels_map: Mapping from block ID (e.g., 'blk_123') to is_anomaly (bool).

    Returns:
        List of LogWindow objects sorted chronologically.
    """
    sessions: Dict[str, List[ParsedLogRecord]] = defaultdict(list)
    unassigned_count = 0

    for rec in records:
        if rec.session_id:
            sessions[rec.session_id].append(rec)
        else:
            unassigned_count += 1

    windows: List[LogWindow] = []

    for block_id, recs in sessions.items():
        # Ensure chronological order within the session by line number / timestamp
        recs.sort(key=lambda r: (r.timestamp if r.timestamp is not None else -1.0, r.line_number))

        start_time = next((r.timestamp for r in recs if r.timestamp is not None), None)
        end_time = next((r.timestamp for r in reversed(recs) if r.timestamp is not None), None)

        # Ground truth lookup: if block not in labels_map, check default or raise error
        if block_id in labels_map:
            is_anomaly = labels_map[block_id]
        else:
            # Explicitly record unmapped block
            is_anomaly = False

        window = LogWindow(
            dataset="hdfs",
            window_id=f"hdfs_session_{block_id}",
            session_id=block_id,
            start_time=start_time,
            end_time=end_time,
            record_count=len(recs),
            template_ids=[r.template_id for r in recs],
            raw_messages=[r.raw_message for r in recs],
            is_anomaly=is_anomaly,
            metadata={
                "first_line": recs[0].line_number,
                "last_line": recs[-1].line_number,
                "has_unknown_template": any(r.template_id == -1 for r in recs),
                "unmapped_label": block_id not in labels_map,
            },
        )
        windows.append(window)

    # Sort windows strictly chronologically by start_time, tie-broken by block_id
    windows.sort(
        key=lambda w: (
            w.start_time if w.start_time is not None else float("inf"),
            w.session_id or "",
        )
    )
    return windows


def build_bgl_fixed_windows(
    records: Iterator[ParsedLogRecord],
    window_size: int = 100,
    min_window_size: int = 1,
) -> List[LogWindow]:
    """Group BGL parsed records into fixed-size sequential chronological windows.

    Args:
        records: Stream of parsed BGL records in chronological file order.
        window_size: Fixed number of records per window.
        min_window_size: Minimum number of records required for the final partial window.

    Returns:
        List of LogWindow objects in chronological sequence.
    """
    windows: List[LogWindow] = []
    current_batch: List[ParsedLogRecord] = []
    window_idx = 0

    for rec in records:
        current_batch.append(rec)
        if len(current_batch) >= window_size:
            window = _create_bgl_window(current_batch, window_idx)
            windows.append(window)
            window_idx += 1
            current_batch = []

    # Final partial window handling
    if len(current_batch) >= min_window_size:
        window = _create_bgl_window(current_batch, window_idx)
        windows.append(window)

    return windows


def _create_bgl_window(recs: List[ParsedLogRecord], window_idx: int) -> LogWindow:
    """Helper to construct a single BGL fixed-size window."""
    start_time = next((r.timestamp for r in recs if r.timestamp is not None), None)
    end_time = next((r.timestamp for r in reversed(recs) if r.timestamp is not None), None)

    # Window is anomalous if ANY record is an alert/anomaly
    is_anomaly = any(r.is_anomaly for r in recs if r.is_anomaly is not None)

    return LogWindow(
        dataset="bgl",
        window_id=f"bgl_window_{window_idx:07d}",
        session_id=None,
        start_time=start_time,
        end_time=end_time,
        record_count=len(recs),
        template_ids=[r.template_id for r in recs],
        raw_messages=[r.raw_message for r in recs],
        is_anomaly=is_anomaly,
        metadata={
            "first_line": recs[0].line_number,
            "last_line": recs[-1].line_number,
            "anomalous_record_count": sum(1 for r in recs if r.is_anomaly),
            "has_unknown_template": any(r.template_id == -1 for r in recs),
        },
    )
