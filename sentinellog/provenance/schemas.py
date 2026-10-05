"""Data schemas and types for Phase 7 citation and provenance engine.

Defines immutable, typed dataclasses for source locations, source artifacts,
evidence provenance records, citations, verification results, and citation bundles.
"""

from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SourceLocation:
    """Exact spatial and temporal coordinates of an evidence record within its source file."""

    source_file: str  # e.g., 'data/processed/hdfs/train.jsonl'
    line_start: Optional[int] = None  # 1-indexed raw log line start
    line_end: Optional[int] = None  # 1-indexed raw log line end
    record_count: int = 0
    session_id: Optional[str] = None  # Block ID for HDFS (blk_-...), None for BGL
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert location to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceLocation":
        """Instantiate location from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class SourceArtifact:
    """Identity and integrity metadata for the physical source file containing the evidence."""

    dataset: str  # 'hdfs' or 'bgl'
    split: str  # 'train' (strictly TRAIN-only for retrieval evidence)
    artifact_path: str  # e.g., 'data/processed/hdfs/train.jsonl'
    artifact_sha256: str  # SHA-256 of the physical file
    pipeline_version: str  # e.g., '0.2.1-phase2-freeze'
    raw_sha256: Optional[str] = None  # SHA-256 of the original raw log file (from Phase 2 manifest)

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact metadata to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceArtifact":
        """Instantiate artifact metadata from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class EvidenceProvenance:
    """Complete provenance chain connecting a selected evidence chunk back to its source."""

    citation_id: str  # Deterministic SHA-256 derivation
    chunk_id: str  # Phase 5 chunk identifier
    dataset: str
    split: str  # Invariant: 'train'
    source_window_id: str
    source_artifact: SourceArtifact
    source_location: SourceLocation
    source_content_hash: str  # Deterministic SHA-256 of canonical exact underlying raw source records
    template_content_hash: str  # Deterministic SHA-256 of normalized Drain3 template token sequence
    content_hash: Optional[str] = None  # Backwards compatibility alias
    provenance_version: str = "1.0"
    source_commit: Optional[str] = None

    def __post_init__(self):
        if self.content_hash is None:
            object.__setattr__(self, "content_hash", self.source_content_hash)

    def to_dict(self) -> Dict[str, Any]:
        """Convert provenance record to serializable dictionary."""
        return {
            "citation_id": self.citation_id,
            "chunk_id": self.chunk_id,
            "dataset": self.dataset,
            "split": self.split,
            "source_window_id": self.source_window_id,
            "source_artifact": self.source_artifact.to_dict(),
            "source_location": self.source_location.to_dict(),
            "source_content_hash": self.source_content_hash,
            "template_content_hash": self.template_content_hash,
            "content_hash": self.content_hash or self.source_content_hash,
            "provenance_version": self.provenance_version,
            "source_commit": self.source_commit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceProvenance":
        """Instantiate provenance record from dictionary."""
        source_hash = data.get("source_content_hash") or data.get("content_hash", "")
        template_hash = data.get("template_content_hash") or data.get("content_hash", "")
        return cls(
            citation_id=data["citation_id"],
            chunk_id=data["chunk_id"],
            dataset=data["dataset"],
            split=data["split"],
            source_window_id=data["source_window_id"],
            source_artifact=SourceArtifact.from_dict(data["source_artifact"]),
            source_location=SourceLocation.from_dict(data["source_location"]),
            source_content_hash=source_hash,
            template_content_hash=template_hash,
            content_hash=data.get("content_hash", source_hash),
            provenance_version=data.get("provenance_version", "1.0"),
            source_commit=data.get("source_commit"),
        )


@dataclass(frozen=True)
class Citation:
    """A human-readable and machine-verifiable evidence citation."""

    citation_id: str
    citation_text: str  # e.g., '[HDFS | train | window=hdfs_session_blk_... | lines=1-5339]'
    chunk_id: str
    source_window_id: str
    dataset: str
    split: str
    selected_rank: int  # Phase 6 evidence rank
    retrieval_score: float  # Original Phase 5 similarity score
    selection_score: float  # Phase 6 MMR score
    source_content_hash: str
    template_content_hash: str
    provenance: EvidenceProvenance
    content_hash: Optional[str] = None

    def __post_init__(self):
        if self.content_hash is None:
            object.__setattr__(self, "content_hash", self.source_content_hash)

    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to serializable dictionary."""
        return {
            "citation_id": self.citation_id,
            "citation_text": self.citation_text,
            "chunk_id": self.chunk_id,
            "source_window_id": self.source_window_id,
            "dataset": self.dataset,
            "split": self.split,
            "selected_rank": self.selected_rank,
            "retrieval_score": self.retrieval_score,
            "selection_score": self.selection_score,
            "source_content_hash": self.source_content_hash,
            "template_content_hash": self.template_content_hash,
            "content_hash": self.content_hash or self.source_content_hash,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        """Instantiate citation from dictionary."""
        source_hash = data.get("source_content_hash") or data.get("content_hash", "")
        template_hash = data.get("template_content_hash") or data.get("content_hash", "")
        return cls(
            citation_id=data["citation_id"],
            citation_text=data["citation_text"],
            chunk_id=data["chunk_id"],
            source_window_id=data["source_window_id"],
            dataset=data["dataset"],
            split=data["split"],
            selected_rank=data["selected_rank"],
            retrieval_score=data["retrieval_score"],
            selection_score=data["selection_score"],
            source_content_hash=source_hash,
            template_content_hash=template_hash,
            content_hash=data.get("content_hash", source_hash),
            provenance=EvidenceProvenance.from_dict(data["provenance"]),
        )


@dataclass
class CitationBundle:
    """An ordered bundle of verified citations for an escalated query window."""

    bundle_id: str  # Deterministic SHA-256 derivation over ordered citation IDs
    query_id: str
    dataset: str
    split: str
    evidence_count: int
    citations: List[Citation]
    provenance_version: str = "1.0"
    source_commit: Optional[str] = None
    all_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to serializable dictionary."""
        return {
            "bundle_id": self.bundle_id,
            "query_id": self.query_id,
            "dataset": self.dataset,
            "split": self.split,
            "evidence_count": self.evidence_count,
            "citations": [c.to_dict() for c in self.citations],
            "provenance_version": self.provenance_version,
            "source_commit": self.source_commit,
            "all_verified": self.all_verified,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationBundle":
        """Instantiate bundle from dictionary."""
        citations = [Citation.from_dict(c) for c in data.get("citations", [])]
        return cls(
            bundle_id=data["bundle_id"],
            query_id=data["query_id"],
            dataset=data["dataset"],
            split=data["split"],
            evidence_count=data["evidence_count"],
            citations=citations,
            provenance_version=data.get("provenance_version", "1.0"),
            source_commit=data.get("source_commit"),
            all_verified=data.get("all_verified", False),
        )


@dataclass
class VerificationResult:
    """The outcome of verifying the integrity and source location of a citation."""

    citation_id: str
    status: str  # "VALID", "INVALID", or "UNRESOLVED"
    content_hash_match: bool
    source_content_hash_match: bool = False
    template_content_hash_match: bool = False
    recomputed_source_hash: Optional[str] = None
    stored_source_hash: Optional[str] = None
    recomputed_template_hash: Optional[str] = None
    stored_template_hash: Optional[str] = None
    recomputed_hash: Optional[str] = None
    stored_hash: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert verification result to dictionary."""
        return asdict(self)

