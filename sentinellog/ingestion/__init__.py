"""SentinelLog Ingestion & Data Pipeline Package.

Exposes log acquisition, Drain3 parsing, session/fixed windowing,
and leakage-safe chronological partitioning.
"""

from sentinellog.ingestion.hasher import compute_sha256, verify_file_integrity
from sentinellog.ingestion.parser import DrainParser
from sentinellog.ingestion.pipeline import (
    read_windows_jsonl,
    run_pipeline,
    write_windows_jsonl,
)
from sentinellog.ingestion.schemas import (
    DataQualityReport,
    DatasetManifest,
    LogWindow,
    ParsedLogRecord,
    UNKNOWN_TEMPLATE_ID,
    UNKNOWN_TEMPLATE_STR,
)
from sentinellog.ingestion.splitter import (
    DataLeakageError,
    chronological_split,
    verify_partition_integrity,
)
from sentinellog.ingestion.windowing import (
    build_bgl_fixed_windows,
    build_hdfs_session_windows,
)

__all__ = [
    "compute_sha256",
    "verify_file_integrity",
    "DrainParser",
    "LogWindow",
    "ParsedLogRecord",
    "DatasetManifest",
    "DataQualityReport",
    "UNKNOWN_TEMPLATE_ID",
    "UNKNOWN_TEMPLATE_STR",
    "build_hdfs_session_windows",
    "build_bgl_fixed_windows",
    "chronological_split",
    "verify_partition_integrity",
    "DataLeakageError",
    "run_pipeline",
    "write_windows_jsonl",
    "read_windows_jsonl",
]
