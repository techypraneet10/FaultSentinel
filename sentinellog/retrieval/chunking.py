"""Contextual chunk construction and deterministic query generation for Phase 5 retrieval.

Converts Phase 2 LogWindow objects into deterministic RetrievalChunk and RetrievalQuery instances.
Enforces that the retrieval corpus is built exclusively from the TRAIN split,
and guarantees that ground-truth anomaly labels are never included in searchable text.
"""

import hashlib
from typing import List, Optional, Sequence

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.guards import (
    guard_no_label_in_text,
    guard_query_does_not_contain_labels,
    guard_train_split_only,
)
from sentinellog.retrieval.schemas import RetrievalChunk, RetrievalQuery
from sentinellog.scoring.artifacts import get_git_commit_sha


def format_template_tokens(template_ids: Sequence[int]) -> str:
    """Format ordered template IDs into a normalized token string.

    Args:
        template_ids: Sequence of integer template IDs (-1 for UNKNOWN).

    Returns:
        Space-separated string of template tokens.
    """
    if not template_ids:
        return ""
    tokens = [f"template_{tid}" if tid >= 0 else "template_unknown" for tid in template_ids]
    return " ".join(tokens)


def compute_chunk_id(dataset: str, split: str, source_window_id: str, text: str) -> str:
    """Derive deterministic SHA-256 identifier for a retrieval chunk.

    Args:
        dataset: Dataset identifier (e.g., 'hdfs', 'bgl').
        split: Dataset split (must be 'train').
        source_window_id: Identifier of the source LogWindow.
        text: Normalized chunk content.

    Returns:
        Hexadecimal SHA-256 string.
    """
    canonical_repr = f"{dataset.strip().lower()}:{split.strip().lower()}:{source_window_id.strip()}:{text}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def build_retrieval_chunk(
    window: LogWindow,
    split: str = "train",
    source_commit: Optional[str] = None,
) -> RetrievalChunk:
    """Construct a historical retrieval chunk from a single TRAIN log window.

    Args:
        window: Source LogWindow.
        split: Partition name (strictly 'train').
        source_commit: Optional Git commit SHA for provenance.

    Returns:
        RetrievalChunk instance.
    """
    guard_train_split_only(split)

    text = format_template_tokens(window.template_ids)
    guard_no_label_in_text(text)

    chunk_id = compute_chunk_id(
        dataset=window.dataset,
        split=split,
        source_window_id=window.window_id,
        text=text,
    )

    provenance = {
        "source_window_id": window.window_id,
        "dataset": window.dataset,
        "split": split,
        "source_commit": source_commit or get_git_commit_sha(),
    }

    return RetrievalChunk(
        chunk_id=chunk_id,
        dataset=window.dataset,
        split=split,
        source_window_id=window.window_id,
        session_id=window.session_id,
        timestamp_start=window.start_time,
        timestamp_end=window.end_time,
        record_count=window.record_count,
        template_ids=list(window.template_ids),
        text=text,
        anomaly_label=bool(window.is_anomaly),  # For evaluation/diagnostics only
        provenance=provenance,
    )


def build_retrieval_corpus(
    windows: Sequence[LogWindow],
    split: str = "train",
    source_commit: Optional[str] = None,
) -> List[RetrievalChunk]:
    """Construct retrieval corpus from a sequence of TRAIN log windows.

    Args:
        windows: Sequence of LogWindow instances from TRAIN.
        split: Partition name (strictly 'train').
        source_commit: Optional Git commit SHA.

    Returns:
        List of RetrievalChunk instances.
    """
    guard_train_split_only(split)
    commit = source_commit or get_git_commit_sha()
    return [build_retrieval_chunk(w, split=split, source_commit=commit) for w in windows]


def build_query_from_window(window: LogWindow) -> RetrievalQuery:
    """Construct a deterministic retrieval query from an escalated window.

    The query strictly uses observable event patterns and does NOT access
    ground-truth anomaly labels.

    Args:
        window: Escalated LogWindow to be investigated.

    Returns:
        RetrievalQuery instance.
    """
    text = format_template_tokens(window.template_ids)
    guard_no_label_in_text(text)

    query = RetrievalQuery(
        query_window_id=window.window_id,
        dataset=window.dataset,
        record_count=window.record_count,
        template_ids=list(window.template_ids),
        text=text,
    )

    guard_query_does_not_contain_labels(query)
    return query
