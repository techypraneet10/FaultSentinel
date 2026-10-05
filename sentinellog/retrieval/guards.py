"""Data leakage, split validation, and label protection guards for Phase 5 retrieval.

Enforces:
1. Rule 1 (Test Set Protection): Test files and test split are strictly forbidden.
2. Corpus Split Invariant: Retrieval corpus must be derived exclusively from TRAIN.
3. Label Leakage Protection: Ground-truth anomaly labels must NEVER appear in searchable text
   or query representation.
"""

from pathlib import Path
from typing import Any, Optional

from sentinellog.scoring.artifacts import TestAccessViolationError, guard_no_test_split


class InvalidSplitError(ValueError):
    """Raised when an operation attempts to construct retrieval corpus from non-train data."""
    pass


class LabelLeakageError(ValueError):
    """Raised when ground-truth anomaly labels leak into searchable retrieval text or queries."""
    pass


def guard_train_split_only(split_name: str, file_path: Optional[str] = None) -> None:
    """Enforce that retrieval corpus construction is restricted strictly to the TRAIN split.

    Args:
        split_name: Name of the partition (must be 'train').
        file_path: Optional file path being accessed.

    Raises:
        TestAccessViolationError: If split is 'test' or points to test files.
        InvalidSplitError: If split is not 'train' (e.g., 'calibration').
    """
    # First enforce Rule 1 test-set protection
    guard_no_test_split(split_name, file_path)

    clean_split = split_name.strip().lower()
    if clean_split != "train":
        raise InvalidSplitError(
            f"Phase 5 retrieval corpus can only be constructed from the 'train' split. "
            f"Attempted to construct corpus from split '{split_name}'. "
            f"Under the default research protocol, CALIBRATION and TEST are strictly prohibited."
        )

    if file_path is not None:
        p = Path(file_path)
        if p.name.lower() != "train.jsonl":
            # If path indicates a split other than train
            for part in p.parts:
                part_lower = part.lower()
                if part_lower in ("calibration.jsonl", "calibration", "test.jsonl", "test"):
                    raise InvalidSplitError(
                        f"Phase 5 corpus guard rejected non-train file path: '{file_path}'. "
                        "Retrieval index must be constructed exclusively from TRAIN data."
                    )


def guard_no_label_in_text(text: str) -> None:
    """Verify that ground-truth anomaly labels do not appear in searchable text.

    Args:
        text: Text string to be embedded or retrieved.

    Raises:
        LabelLeakageError: If label indicator patterns are detected.
    """
    leakage_indicators = [
        "is_anomaly",
        "anomaly_label",
        "ground_truth",
        "is_anomaly=true",
        "is_anomaly=false",
        "label: anomaly",
        "label: normal",
    ]
    text_lower = text.lower()
    for indicator in leakage_indicators:
        if indicator in text_lower:
            raise LabelLeakageError(
                f"Label Leakage Detected: Searchable text contains label indicator '{indicator}'. "
                "Ground-truth anomaly labels must NEVER be exposed in searchable content."
            )


def guard_query_does_not_contain_labels(query: Any) -> None:
    """Verify that a query object or query text does not contain ground-truth anomaly labels.

    Args:
        query: Query object or dictionary.

    Raises:
        LabelLeakageError: If query contains label attributes or leaked text.
    """
    if hasattr(query, "is_anomaly") and getattr(query, "is_anomaly") is not None:
        raise LabelLeakageError(
            "Query object contains 'is_anomaly' attribute. "
            "Retrieval queries must not have access to ground-truth anomaly labels at escalation time."
        )
    if hasattr(query, "anomaly_label") and getattr(query, "anomaly_label") is not None:
        raise LabelLeakageError(
            "Query object contains 'anomaly_label' attribute. "
            "Retrieval queries must not have access to ground-truth anomaly labels."
        )

    if hasattr(query, "text") and isinstance(query.text, str):
        guard_no_label_in_text(query.text)
    elif isinstance(query, dict) and "text" in query:
        guard_no_label_in_text(str(query["text"]))
