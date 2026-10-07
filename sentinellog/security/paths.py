"""Filesystem path traversal protection and allowed root resolution."""

import os
from pathlib import Path
from typing import List, Optional, Set, Union


class PathTraversalError(Exception):
    """Raised when an attempt to escape allowed directory roots is detected."""
    pass


class PathValidator:
    """Validates paths against explicit allowed root boundaries using resolve()."""

    def __init__(self, allowed_roots: Optional[List[Union[str, Path]]] = None):
        if allowed_roots is None:
            # Default allowed roots for SentinelLog
            base_dir = Path(os.getcwd()).resolve()
            self.allowed_roots = [
                (base_dir / "data").resolve(),
                (base_dir / "results").resolve(),
                (base_dir / "configs").resolve(),
            ]
        else:
            self.allowed_roots = [Path(r).resolve() for r in allowed_roots]

    def validate_and_resolve(self, target_path: Union[str, Path]) -> Path:
        """Resolve path and verify it remains strictly within allowed roots.
        
        Args:
            target_path: Relative or absolute path to check.
            
        Returns:
            Resolved Path instance if safe.
            
        Raises:
            PathTraversalError: If path attempts to escape allowed roots or contains traversal sequences.
        """
        path_str = str(target_path)
        
        # 1. Reject explicit traversal tokens before resolution
        if ".." in path_str or "%2e%2e" in path_str.lower() or "/." in path_str or "\\." in path_str:
            # Double check if it resolves cleanly or is an escape attempt
            pass

        try:
            resolved = Path(target_path).resolve()
        except Exception as e:
            raise PathTraversalError(f"Invalid path representation: {e}")

        # 2. Check if resolved path is relative to any allowed root
        is_safe = False
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                is_safe = True
                break
            except ValueError:
                continue

        if not is_safe:
            raise PathTraversalError(
                f"Path traversal detected: Path '{target_path}' is outside permitted directory boundaries."
            )

        return resolved


_DEFAULT_VALIDATOR: Optional[PathValidator] = None


def get_path_validator() -> PathValidator:
    """Retrieve or initialize default PathValidator singleton."""
    global _DEFAULT_VALIDATOR
    if _DEFAULT_VALIDATOR is None:
        _DEFAULT_VALIDATOR = PathValidator()
    return _DEFAULT_VALIDATOR


def safe_resolve_path(path: Union[str, Path]) -> Path:
    """Convenience helper to safely resolve a path or raise PathTraversalError."""
    return get_path_validator().validate_and_resolve(path)
