"""Strict validation and input guardrails for Phase 8 Reasoning Engine.

Enforces:
1. Strict label leakage prevention: forbids anomaly labels, ground truth, or target labels.
2. Partition guards: forbids test partition lookups (Rule 1).
3. Provenance gate: verifies that citations satisfy Phase 7 integrity checks before reasoning.
"""

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sentinellog.provenance.hashing import compute_citation_id
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.exceptions import (
    InvalidSplitError,
    LabelLeakageError,
    ProvenanceInvalidError,
)
from sentinellog.scoring.artifacts import guard_no_test_split

FORBIDDEN_LABEL_KEYS: Set[str] = {
    "anomaly_label",
    "is_anomaly",
    "label",
    "ground_truth",
    "target",
    "y_true",
    "true_label",
}


def validate_no_label_leakage(obj: Any, path: str = "root") -> None:
    """Recursively inspect an object or structure to ensure no ground-truth labels are present.

    Args:
        obj: Dict, list, or primitive object to inspect.
        path: Path identifier for descriptive error reporting.

    Raises:
        LabelLeakageError: If any forbidden label keys are found with non-null values.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            clean_k = k.strip().lower()
            if clean_k in FORBIDDEN_LABEL_KEYS and v is not None:
                raise LabelLeakageError(
                    f"Label leakage detected at '{path}.{k}' with value '{v}'. "
                    f"Phase 8 reasoning must remain strictly label-free."
                )
            validate_no_label_leakage(v, path=f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            validate_no_label_leakage(item, path=f"{path}[{i}]")


def validate_reasoning_split(split: str, allowed_splits: Sequence[str] = ("calibration", "train")) -> None:
    """Ensure data split is strictly permitted and never 'test'.

    Args:
        split: Partition identifier.
        allowed_splits: Sequence of permitted partition names.

    Raises:
        InvalidSplitError: If split is 'test' or not in allowed splits.
    """
    clean_split = split.strip().lower()
    guard_no_test_split(clean_split)

    if clean_split not in allowed_splits:
        raise InvalidSplitError(
            f"Split '{split}' is not permitted for Phase 8 reasoning. "
            f"Allowed splits: {allowed_splits}."
        )


def validate_provenance_gate(
    bundle: Optional[CitationBundle],
    dataset: str,
    strict: bool = True,
) -> Tuple[bool, str]:
    """Validate that evidence bundle passes complete Phase 7 provenance and addressability checks.

    Args:
        bundle: CitationBundle object containing evidence citations.
        dataset: Target dataset name.
        strict: If True, requires all_verified is True and non-empty citations for escalated windows.

    Returns:
        Tuple of (is_valid: bool, status_message: str).
    """
    if bundle is None:
        return False, "No citation bundle provided."

    if bundle.dataset.strip().lower() != dataset.strip().lower():
        return False, f"Citation bundle dataset mismatch: expected '{dataset}', got '{bundle.dataset}'."

    # Verify that test split is not cited
    if bundle.split.strip().lower() != "train":
        return False, f"Citation bundle split must be strictly 'train', got '{bundle.split}'."

    if strict and not bundle.all_verified:
        return False, "Citation bundle failed Phase 7 integrity checks (all_verified is False)."

    # Verify individual citations
    for idx, cit in enumerate(bundle.citations):
        if not cit.citation_id or len(cit.citation_id) != 64:
            return False, f"Citation at index {idx} has invalid or missing citation_id."

        if not cit.source_content_hash or len(cit.source_content_hash) != 64:
            return False, f"Citation at index {idx} has invalid source_content_hash."

        if not cit.template_content_hash or len(cit.template_content_hash) != 64:
            return False, f"Citation at index {idx} has invalid template_content_hash."

        # Verify citation ID determinism against location
        loc = cit.provenance.source_location
        expected_cid = compute_citation_id(
            dataset=cit.dataset,
            split=cit.split,
            chunk_id=cit.chunk_id,
            source_window_id=cit.source_window_id,
            line_start=loc.line_start,
            line_end=loc.line_end,
        )
        if cit.citation_id != expected_cid:
            return False, (
                f"Citation ID mismatch at index {idx}: expected '{expected_cid}', "
                f"got '{cit.citation_id}'."
            )

    return True, "VERIFIED"
