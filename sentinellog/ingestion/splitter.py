"""Chronological dataset partitioning and leakage verification.

Enforces strict temporal ordering and boundary isolation across
Train (60%), Calibration (20%), and Test (20%) partitions.
"""

from typing import Dict, List, Optional, Set, Tuple

from sentinellog.ingestion.schemas import LogWindow


class DataLeakageError(ValueError):
    """Raised when partition overlap or chronological inversion is detected."""
    pass


def chronological_split(
    windows: List[LogWindow],
    train_ratio: float = 0.60,
    calib_ratio: float = 0.20,
    test_ratio: float = 0.20,
    snap_to_timestamp_boundary: bool = True,
) -> Tuple[List[LogWindow], List[LogWindow], List[LogWindow]]:
    """Partition windows chronologically into train, calibration, and test splits.

    Windows must be ordered chronologically by (start_time, first_line, session_id).

    Args:
        windows: List of LogWindow objects, strictly ordered chronologically.
        train_ratio: Fraction of windows for training (default 0.60).
        calib_ratio: Fraction of windows for conformal calibration (default 0.20).
        test_ratio: Fraction of windows for frozen testing (default 0.20).
        snap_to_timestamp_boundary: If True and timestamps are present, adjust split
            points to the nearest timestamp boundary to guarantee strict inequality
            max(train) < min(calib) and max(calib) < min(test).

    Returns:
        Tuple of (train_windows, calibration_windows, test_windows).

    Raises:
        ValueError: If split ratios do not sum to 1.0 or window list is empty.
        DataLeakageError: If partitions violate temporal isolation or ID disjointness.
    """
    if not windows:
        raise ValueError("Cannot split an empty window list.")

    ratio_sum = train_ratio + calib_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError(
            f"Split ratios must sum to 1.0; got {train_ratio} + {calib_ratio} + {test_ratio} = {ratio_sum}"
        )

    n_total = len(windows)
    target_train_idx = int(n_total * train_ratio)
    target_calib_end_idx = int(n_total * (train_ratio + calib_ratio))

    if snap_to_timestamp_boundary and any(w.start_time is not None for w in windows):
        train_idx = _find_timestamp_cut(windows, target_train_idx)
        calib_end_idx = _find_timestamp_cut(windows, target_calib_end_idx)
    else:
        train_idx = target_train_idx
        calib_end_idx = target_calib_end_idx

    train_windows = windows[:train_idx]
    calib_windows = windows[train_idx:calib_end_idx]
    test_windows = windows[calib_end_idx:]

    # Verify split integrity and absence of data leakage
    verify_partition_integrity(
        train_windows,
        calib_windows,
        test_windows,
        require_strict_timestamp_inequality=snap_to_timestamp_boundary,
    )

    return train_windows, calib_windows, test_windows


def _find_timestamp_cut(windows: List[LogWindow], target_idx: int) -> int:
    """Find a cut point near target_idx where window[cut-1].start_time < window[cut].start_time."""
    if target_idx <= 0 or target_idx >= len(windows):
        return target_idx

    target_time = windows[target_idx].start_time
    if target_time is None:
        return target_idx

    # Check if target_idx already falls on a timestamp change
    prev_time = windows[target_idx - 1].start_time
    if prev_time is not None and prev_time < target_time:
        return target_idx

    # Otherwise, step backward to find where target_time started
    left_cut = target_idx
    while left_cut > 1 and windows[left_cut - 1].start_time == target_time:
        left_cut -= 1

    # Check if left_cut provides a valid strict timestamp boundary
    if left_cut > 0 and windows[left_cut - 1].start_time is not None:
        if windows[left_cut - 1].start_time < windows[left_cut].start_time:
            return left_cut

    # Fallback: step forward to find next timestamp change
    right_cut = target_idx
    while right_cut < len(windows) - 1 and windows[right_cut].start_time == target_time:
        right_cut += 1

    if right_cut < len(windows) and windows[right_cut - 1].start_time < windows[right_cut].start_time:
        return right_cut

    return target_idx


def verify_partition_integrity(
    train: List[LogWindow],
    calib: List[LogWindow],
    test: List[LogWindow],
    require_strict_timestamp_inequality: bool = False,
) -> None:
    """Validate that partitions have zero ID overlap and follow strict chronological boundaries.

    Raises:
        DataLeakageError: If any leakage or boundary violation is detected.
    """
    train_ids: Set[str] = {w.window_id for w in train}
    calib_ids: Set[str] = {w.window_id for w in calib}
    test_ids: Set[str] = {w.window_id for w in test}

    # 1. Window ID Disjointness
    if train_ids & calib_ids:
        raise DataLeakageError(
            f"Window ID overlap detected between train and calib: {len(train_ids & calib_ids)} IDs."
        )
    if train_ids & test_ids:
        raise DataLeakageError(
            f"Window ID overlap detected between train and test: {len(train_ids & test_ids)} IDs."
        )
    if calib_ids & test_ids:
        raise DataLeakageError(
            f"Window ID overlap detected between calib and test: {len(calib_ids & test_ids)} IDs."
        )

    # 2. Session ID Disjointness (e.g. HDFS blocks)
    train_sessions = {w.session_id for w in train if w.session_id}
    calib_sessions = {w.session_id for w in calib if w.session_id}
    test_sessions = {w.session_id for w in test if w.session_id}

    if train_sessions & calib_sessions:
        raise DataLeakageError(
            f"Session ID overlap between train and calib: {len(train_sessions & calib_sessions)} sessions."
        )
    if train_sessions & test_sessions:
        raise DataLeakageError(
            f"Session ID overlap between train and test: {len(train_sessions & test_sessions)} sessions."
        )
    if calib_sessions & test_sessions:
        raise DataLeakageError(
            f"Session ID overlap between calib and test: {len(calib_sessions & test_sessions)} sessions."
        )

    # 3. Chronological Boundary Check
    train_times = [w.start_time for w in train if w.start_time is not None]
    calib_times = [w.start_time for w in calib if w.start_time is not None]
    test_times = [w.start_time for w in test if w.start_time is not None]

    if train_times and calib_times:
        max_train = max(train_times)
        min_calib = min(calib_times)
        if require_strict_timestamp_inequality:
            if max_train >= min_calib:
                raise DataLeakageError(
                    f"Strict chronological boundary violation between train and calib: max_train={max_train} >= min_calib={min_calib}"
                )
        else:
            if max_train > min_calib:
                raise DataLeakageError(
                    f"Chronological inversion between train and calib: max_train={max_train} > min_calib={min_calib}"
                )

    if calib_times and test_times:
        max_calib = max(calib_times)
        min_test = min(test_times)
        if require_strict_timestamp_inequality:
            if max_calib >= min_test:
                raise DataLeakageError(
                    f"Strict chronological boundary violation between calib and test: max_calib={max_calib} >= min_test={min_test}"
                )
        else:
            if max_calib > min_test:
                raise DataLeakageError(
                    f"Chronological inversion between calib and test: max_calib={max_calib} > min_test={min_test}"
                )


def get_split_summary(
    train: List[LogWindow],
    calib: List[LogWindow],
    test: List[LogWindow],
) -> Dict[str, Dict[str, int]]:
    """Return summary statistics of the partition sizes and anomaly counts."""
    return {
        "train": {
            "total_windows": len(train),
            "anomalous_windows": sum(1 for w in train if w.is_anomaly),
            "normal_windows": sum(1 for w in train if not w.is_anomaly),
        },
        "calibration": {
            "total_windows": len(calib),
            "anomalous_windows": sum(1 for w in calib if w.is_anomaly),
            "normal_windows": sum(1 for w in calib if not w.is_anomaly),
        },
        "test": {
            "total_windows": len(test),
            "anomalous_windows": sum(1 for w in test if w.is_anomaly),
            "normal_windows": sum(1 for w in test if not w.is_anomaly),
        },
    }
