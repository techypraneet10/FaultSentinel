"""Hashing and raw data integrity utilities for SentinelLog.

Computes and verifies SHA-256 checksums to ensure experimental reproducibility
and dataset traceability.
"""

import hashlib
from pathlib import Path
from typing import Dict, Union


def compute_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file deterministically.

    Args:
        file_path: Path to the target file.
        chunk_size: Byte size of chunks read into memory.

    Returns:
        Hexadecimal SHA-256 checksum string.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    """Calculate the SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_file_integrity(file_path: Union[str, Path], expected_sha256: str) -> bool:
    """Verify that a file matches its expected SHA-256 hash.

    Args:
        file_path: Target file path.
        expected_sha256: Expected hexadecimal SHA-256 string.

    Returns:
        True if hashes match, False otherwise.
    """
    actual_hash = compute_sha256(file_path)
    return actual_hash.lower() == expected_sha256.strip().lower()


def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, Union[str, int]]:
    """Return dictionary of file metadata including size and SHA-256."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    return {
        "filename": path.name,
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": compute_sha256(path),
    }
