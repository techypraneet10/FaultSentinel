"""Source resolution engine for Phase 7 evidence provenance.

Locates the exact physical source record in data/processed/<dataset>/train.jsonl,
extracts spatial coordinates (line numbers, record count, session/block ID),
and recomputes canonical content representations and fingerprints.

Guarantees:
1. Exact source resolution: fails closed if source cannot be found.
2. TRAIN-only partition invariant: rejects non-train lookups.
3. Test set protection: strictly forbids test partition access.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from sentinellog.provenance.hashing import compute_content_hash
from sentinellog.provenance.schemas import SourceArtifact, SourceLocation
from sentinellog.retrieval.chunking import format_template_tokens
from sentinellog.retrieval.guards import guard_train_split_only
from sentinellog.scoring.artifacts import compute_sha256, guard_no_test_split


class ProvenanceResolutionError(Exception):
    """Raised when an evidence citation or source window cannot be resolved."""
    pass


class SourceResolver:
    """Resolves historical source windows from physical Phase 2 artifacts with in-memory caching."""

    def __init__(self, data_root: str = "data/processed"):
        """Initialize resolver.

        Args:
            data_root: Root directory for processed dataset partitions.
        """
        self.data_root = data_root
        self._window_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}  # {dataset: {window_id: record}}
        self._artifact_cache: Dict[str, SourceArtifact] = {}  # {dataset: SourceArtifact}

    def _ensure_dataset_loaded(self, dataset: str) -> None:
        """Load and index the TRAIN partition for the specified dataset."""
        clean_ds = dataset.strip().lower()
        if clean_ds in self._window_cache:
            return

        guard_train_split_only("train")
        train_file = os.path.join(self.data_root, clean_ds, "train.jsonl")
        manifest_file = os.path.join(self.data_root, clean_ds, "manifest.json")

        guard_no_test_split("train", train_file)

        if not os.path.exists(train_file):
            raise ProvenanceResolutionError(
                f"Source artifact file does not exist: '{train_file}'. Cannot resolve provenance."
            )

        # Compute physical artifact SHA-256
        artifact_sha256 = compute_sha256(train_file)

        # Load Phase 2 manifest if available
        pipeline_version = "0.2.0-phase2"
        raw_sha256 = None
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                pipeline_version = m_data.get("pipeline_version", pipeline_version)
                raw_sha256 = m_data.get("raw_sha256")
            except Exception:
                pass

        source_artifact = SourceArtifact(
            dataset=clean_ds,
            split="train",
            artifact_path=train_file.replace("\\", "/"),
            artifact_sha256=artifact_sha256,
            pipeline_version=pipeline_version,
            raw_sha256=raw_sha256,
        )
        self._artifact_cache[clean_ds] = source_artifact

        # Index all windows by window_id
        index: Dict[str, Dict[str, Any]] = {}
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    wid = rec.get("window_id")
                    if wid:
                        index[wid] = rec

        self._window_cache[clean_ds] = index

    def resolve_source(
        self,
        dataset: str,
        split: str,
        source_window_id: str,
    ) -> Tuple[SourceArtifact, SourceLocation, str, str]:
        """Resolve exact source coordinates and content for a given window.

        Args:
            dataset: Dataset name ('hdfs' or 'bgl').
            split: Partition name (strictly 'train').
            source_window_id: Identifier of the source window.

        Returns:
            Tuple of:
                - SourceArtifact: metadata describing the physical source file
                - SourceLocation: exact spatial and line coordinates
                - canonical_text: reconstructed observable template token text
                - content_hash: SHA-256 fingerprint of canonical text

        Raises:
            ProvenanceResolutionError: If source cannot be found or split is invalid.
        """
        guard_train_split_only(split)
        clean_ds = dataset.strip().lower()

        self._ensure_dataset_loaded(clean_ds)

        artifact = self._artifact_cache[clean_ds]
        ds_index = self._window_cache[clean_ds]

        if source_window_id not in ds_index:
            raise ProvenanceResolutionError(
                f"Source window '{source_window_id}' not found in artifact '{artifact.artifact_path}'. "
                f"Resolution failed closed."
            )

        win_data = ds_index[source_window_id]
        meta = win_data.get("metadata", {})

        location = SourceLocation(
            source_file=artifact.artifact_path,
            line_start=meta.get("first_line"),
            line_end=meta.get("last_line"),
            record_count=win_data.get("record_count", 0),
            session_id=win_data.get("session_id"),
            timestamp_start=win_data.get("start_time"),
            timestamp_end=win_data.get("end_time"),
        )

        template_ids = win_data.get("template_ids", [])
        canonical_text = format_template_tokens(template_ids)
        content_hash = compute_content_hash(canonical_text)

        return artifact, location, canonical_text, content_hash
