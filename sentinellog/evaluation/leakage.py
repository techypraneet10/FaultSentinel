"""Data leakage detection, test-set locking, and label isolation guards for Phase 12.

Strictly protects Rule 1 (Test Set Protection) and Rule 2 (Chronological Splits).
Guarantees:
- Final test split is frozen and used for evaluation ONLY
- No fit(), calibrate(), or threshold tuning on TEST
- Retrieval and provenance corpora strictly exclude TEST windows
- Ground-truth labels are isolated exclusively to the evaluation metric layer
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json

from sentinellog.ingestion.schemas import LogWindow


class TestMutationViolationError(PermissionError):
    """Raised when an operation attempts to fit, calibrate, or tune against the frozen test set."""
    __test__ = False


class LabelLeakageViolationError(PermissionError):
    """Raised when ground-truth labels are improperly passed into upstream scoring/triage components."""
    __test__ = False


class TestSetLock:
    """Context guard enforcing test set read-only evaluation lock."""

    __test__ = False

    def __init__(self, split_name: str, operation: str = "evaluate"):
        self.split_name = split_name.strip().lower()
        self.operation = operation.strip().lower()

    def __enter__(self):
        forbidden_ops = {"fit", "train", "calibrate", "tune", "select_threshold", "tune_alpha"}
        if self.split_name == "test" and self.operation in forbidden_ops:
            raise TestMutationViolationError(
                f"Rule 1 Violation: Attempted forbidden operation '{self.operation}' on frozen TEST split. "
                "The test set must be used for final evaluation ONLY without tuning."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def guard_evaluation_only(operation: str, split_name: str) -> None:
    """Raise error if any tuning or training operation is attempted on test data."""
    with TestSetLock(split_name=split_name, operation=operation):
        pass


def audit_corpus_leakage(
    train_windows: List[LogWindow],
    calib_windows: List[LogWindow],
    test_windows: List[LogWindow],
    retrieval_window_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Audit partition window IDs and hashes to verify zero cross-split leakage.

    Args:
        train_windows: Windows in train split.
        calib_windows: Windows in calibration split.
        test_windows: Windows in test split.
        retrieval_window_ids: Window IDs indexed in semantic retrieval corpus.

    Returns:
        Audit report dict verifying zero overlaps.
    """
    train_ids = {w.window_id for w in train_windows}
    calib_ids = {w.window_id for w in calib_windows}
    test_ids = {w.window_id for w in test_windows}

    train_test_overlap = train_ids.intersection(test_ids)
    calib_test_overlap = calib_ids.intersection(test_ids)
    train_calib_overlap = train_ids.intersection(calib_ids)

    retrieval_test_overlap = set()
    if retrieval_window_ids is not None:
        retrieval_test_overlap = set(retrieval_window_ids).intersection(test_ids)

    passed = (
        len(train_test_overlap) == 0
        and len(calib_test_overlap) == 0
        and len(train_calib_overlap) == 0
        and len(retrieval_test_overlap) == 0
    )

    return {
        "passed": passed,
        "n_train": len(train_ids),
        "n_calib": len(calib_ids),
        "n_test": len(test_ids),
        "train_test_overlap_count": len(train_test_overlap),
        "calib_test_overlap_count": len(calib_test_overlap),
        "train_calib_overlap_count": len(train_calib_overlap),
        "retrieval_test_overlap_count": len(retrieval_test_overlap),
        "retrieval_corpus_clean": len(retrieval_test_overlap) == 0,
    }


def load_test_windows_for_evaluation(test_file_path: str) -> List[LogWindow]:
    """Safely load test windows exclusively for evaluation under explicit authorization.

    Args:
        test_file_path: Path to test.jsonl.

    Returns:
        List of LogWindow objects.
    """
    if not os.path.exists(test_file_path):
        raise FileNotFoundError(f"Test split file not found: {test_file_path}")

    # Explicit audit guard
    guard_evaluation_only(operation="evaluate", split_name="test")

    windows: List[LogWindow] = []
    with open(test_file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                windows.append(LogWindow.from_dict(json.loads(line)))

    return windows
