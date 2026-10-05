"""Data schemas and types for SentinelLog ingestion and preprocessing.

Defines typed dataclasses for raw logs, parsed records, session/fixed windows,
and pipeline manifests.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


UNKNOWN_TEMPLATE_ID = -1
UNKNOWN_TEMPLATE_STR = "UNKNOWN"


@dataclass
class RawLogRecord:
    """Represents an unparsed, raw log line and its file position."""

    dataset: str
    line_number: int
    raw_text: str
    timestamp_raw: Optional[str] = None
    identifier: Optional[str] = None


@dataclass
class ParsedLogRecord:
    """Represents a structured record produced by the Drain3 parser."""

    dataset: str
    line_number: int
    timestamp: Optional[float]  # Epoch timestamp (seconds), or None if unavailable
    timestamp_str: Optional[str]
    session_id: Optional[str]  # e.g., HDFS block ID (blk_-...)
    log_level: Optional[str]
    component: Optional[str]
    raw_message: str
    template: str
    template_id: int  # -1 for UNKNOWN
    is_anomaly: Optional[bool]  # True/False if record-level ground truth exists


@dataclass
class LogWindow:
    """Represents an aggregated sequence of log events for downstream triage."""

    dataset: str
    window_id: str
    session_id: Optional[str]
    start_time: Optional[float]
    end_time: Optional[float]
    record_count: int
    template_ids: List[int]
    raw_messages: List[str]
    is_anomaly: bool  # Ground-truth window label
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert window to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogWindow":
        """Instantiate window from dictionary."""
        return cls(**data)


@dataclass
class DatasetManifest:
    """Provenance and integrity metadata for a dataset artifact."""

    dataset_name: str
    source_url: Optional[str]
    acquisition_timestamp: str
    raw_filename: str
    raw_file_size_bytes: int
    raw_sha256: str
    pipeline_version: str
    parser_config_version: str
    windowing_config: Dict[str, Any]
    split_config: Dict[str, Any]
    counts: Dict[str, int]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualityReport:
    """Quality and validation report for parsed datasets and constructed windows."""

    dataset_name: str
    generated_at: str
    source_file_count: int
    raw_bytes: int
    raw_sha256: str
    total_raw_records: int
    successfully_parsed_records: int
    unknown_template_records: int
    unique_template_count: int
    total_windows: int
    train_windows: int
    calibration_windows: int
    test_windows: int
    anomalous_windows: int
    normal_windows: int
    missing_timestamps_count: int
    duplicate_window_ids_count: int
    leakage_check_passed: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
