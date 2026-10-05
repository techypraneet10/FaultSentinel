"""Deterministic cryptographic hashing and citation formatting utilities for Phase 7.

Provides:
1. Canonical text content hashing via SHA-256.
2. Deterministic derivation of citation IDs.
3. Deterministic derivation of citation bundle IDs.
4. Human-readable canonical citation formatting.
"""

import hashlib
from typing import List, Optional, Sequence, Union

from sentinellog.provenance.schemas import SourceLocation


def compute_canonical_source_text(raw_records: Sequence[str]) -> str:
    """Derive deterministic canonical representation of raw source records.

    Canonical representation strips individual record strings and joins them by newline,
    with enclosing whitespace trimmed.

    Args:
        raw_records: Sequence of raw log message strings from source records.

    Returns:
        Deterministic canonical raw source text.
    """
    return "\n".join(r.strip() for r in raw_records).strip()


def compute_source_content_hash(raw_records: Union[str, Sequence[str]]) -> str:
    """Compute deterministic SHA-256 fingerprint over canonical raw source records.

    Guarantees exact source-record integrity. Does NOT depend on template tokenization.

    Args:
        raw_records: Sequence of raw log message strings or pre-canonicalized string.

    Returns:
        Hexadecimal SHA-256 string.
    """
    if isinstance(raw_records, str):
        canonical_text = raw_records.strip()
    else:
        canonical_text = compute_canonical_source_text(raw_records)
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def compute_template_content_hash(text: str) -> str:
    """Compute deterministic SHA-256 fingerprint over normalized Drain3 template token sequence.

    Args:
        text: Observable template token representation of chunk.

    Returns:
        Hexadecimal SHA-256 string.
    """
    canonical_text = text.strip()
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def compute_content_hash(text: str) -> str:
    """Backwards-compatible wrapper for template content hash.

    Args:
        text: Observable template token representation of chunk.

    Returns:
        Hexadecimal SHA-256 string.
    """
    return compute_template_content_hash(text)


def compute_citation_id(
    dataset: str,
    split: str,
    chunk_id: str,
    source_window_id: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> str:
    """Derive deterministic SHA-256 identifier for an evidence citation.

    Canonically serialized as:
        dataset:split:chunk_id:source_window_id:line_start:line_end

    Args:
        dataset: Dataset identifier ('hdfs' or 'bgl').
        split: Partition name (strictly 'train').
        chunk_id: Phase 5 chunk identifier.
        source_window_id: Source window identifier.
        line_start: Optional 1-indexed start line.
        line_end: Optional 1-indexed end line.

    Returns:
        Hexadecimal SHA-256 string.
    """
    l_start_str = str(line_start) if line_start is not None else "none"
    l_end_str = str(line_end) if line_end is not None else "none"
    canonical_repr = (
        f"{dataset.strip().lower()}:{split.strip().lower()}:"
        f"{chunk_id.strip()}:{source_window_id.strip()}:"
        f"{l_start_str}:{l_end_str}"
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def compute_bundle_id(
    citation_ids: Sequence[str],
    dataset: str,
    provenance_version: str = "1.0",
) -> str:
    """Derive deterministic SHA-256 identifier for an ordered citation bundle.

    Args:
        citation_ids: Ordered sequence of citation IDs matching evidence rank.
        dataset: Target dataset name ('hdfs' or 'bgl').
        provenance_version: Provenance schema version string.

    Returns:
        Hexadecimal SHA-256 string.
    """
    joined_ids = ",".join(c.strip() for c in citation_ids)
    canonical_repr = f"{dataset.strip().lower()}:{provenance_version.strip()}:{joined_ids}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def format_citation_text(
    dataset: str,
    split: str,
    source_window_id: str,
    location: SourceLocation,
) -> str:
    """Format an unambiguous, deterministic, human-readable citation string.

    Format examples:
        - HDFS: [HDFS | train | window=hdfs_session_blk_-1608999687919862906 | lines=1-5339 | records=249]
        - BGL:  [BGL | train | window=bgl_window_0000000 | lines=1-100 | records=100]

    Args:
        dataset: Dataset identifier.
        split: Partition name.
        source_window_id: Source window identifier.
        location: SourceLocation object.

    Returns:
        Formatted citation string.
    """
    parts = [
        dataset.upper(),
        split.lower(),
        f"window={source_window_id}",
    ]
    if location.line_start is not None and location.line_end is not None:
        parts.append(f"lines={location.line_start}-{location.line_end}")
    elif location.line_start is not None:
        parts.append(f"line={location.line_start}")

    if location.record_count > 0:
        parts.append(f"records={location.record_count}")

    return f"[{' | '.join(parts)}]"
