"""Drain3 log parser component for SentinelLog.

Extracts structured events and templates from raw log messages using the Drain3
streaming tree algorithm, maintaining explicit representations for unknown or
unparseable templates.
"""

from datetime import datetime
import re
from typing import Any, Dict, Iterator, List, Optional

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

from sentinellog.ingestion.schemas import (
    ParsedLogRecord,
    UNKNOWN_TEMPLATE_ID,
    UNKNOWN_TEMPLATE_STR,
)


# Default masking instructions for variable fields
DEFAULT_HDFS_MASKING = [
    MaskingInstruction(r"blk_-?\d+", "<*>"),
    MaskingInstruction(r"(/[\w.\-]+)+", "<*>"),
    MaskingInstruction(r"(\d+\.){3}\d+(:\d+)?", "<*>"),
    MaskingInstruction(r"\b\d+\b", "<*>"),
]

DEFAULT_BGL_MASKING = [
    MaskingInstruction(r"core\.\d+", "<*>"),
    MaskingInstruction(r"0x[0-9a-fA-F]+", "<*>"),
    MaskingInstruction(r"(\d+\.){3}\d+", "<*>"),
    MaskingInstruction(r"\b\d+\b", "<*>"),
]

# HDFS Log Format regex: <Date> <Time> <Pid> <Level> <Component>: <Content>
HDFS_REGEX = re.compile(
    r"^(\d{6})\s+(\d{6})\s+(\d+)\s+([A-Za-z]+)\s+([^:]+):\s+(.*)$"
)
HDFS_BLOCK_ID_REGEX = re.compile(r"(blk_-?\d+)")


class DrainParser:
    """Stream-capable Drain3 parser with dataset-specific header extraction."""

    def __init__(
        self,
        dataset: str = "hdfs",
        sim_th: float = 0.5,
        depth: int = 4,
        max_children: int = 100,
        custom_masking: Optional[List[MaskingInstruction]] = None,
    ):
        self.dataset = dataset.lower()
        self.sim_th = sim_th
        self.depth = depth
        self.max_children = max_children

        # Configure Drain3 TemplateMiner
        config = TemplateMinerConfig()
        config.drain_sim_th = sim_th
        config.drain_depth = depth
        config.drain_max_children = max_children

        if custom_masking is not None:
            config.masking_instructions = custom_masking
        elif self.dataset == "hdfs":
            config.masking_instructions = DEFAULT_HDFS_MASKING
        elif self.dataset == "bgl":
            config.masking_instructions = DEFAULT_BGL_MASKING
        else:
            config.masking_instructions = []

        self.miner = TemplateMiner(config=config)
        self.frozen = False

        # Statistics
        self.total_records = 0
        self.parsed_records = 0
        self.unknown_records = 0

    def freeze(self) -> None:
        """Freeze template vocabulary. Subsequent parsing will match without adding new clusters."""
        self.frozen = True

    @property
    def is_frozen(self) -> bool:
        """Whether the parser vocabulary is frozen."""
        return self.frozen

    def parse_hdfs_line(self, line: str, line_number: int) -> ParsedLogRecord:
        """Parse a single raw HDFS log record."""
        line = line.strip()
        match = HDFS_REGEX.match(line)
        if not match:
            self.unknown_records += 1
            return ParsedLogRecord(
                dataset="hdfs",
                line_number=line_number,
                timestamp=None,
                timestamp_str=None,
                session_id=self._extract_hdfs_block_id(line),
                log_level=None,
                component=None,
                raw_message=line,
                template=UNKNOWN_TEMPLATE_STR,
                template_id=UNKNOWN_TEMPLATE_ID,
                is_anomaly=None,
            )

        date_str, time_str, pid, level, component, content = match.groups()
        full_time_str = f"{date_str} {time_str}"
        epoch_time = self._parse_hdfs_timestamp(date_str, time_str)
        block_id = self._extract_hdfs_block_id(content) or self._extract_hdfs_block_id(line)

        try:
            if not self.frozen:
                result = self.miner.add_log_message(content)
                template = result.get("template_mined", UNKNOWN_TEMPLATE_STR)
                template_id = int(result.get("cluster_id", UNKNOWN_TEMPLATE_ID))
                self.parsed_records += 1
            else:
                cluster = self.miner.match(content)
                if cluster is not None:
                    template = cluster.get_template()
                    template_id = int(cluster.cluster_id)
                    self.parsed_records += 1
                else:
                    template = UNKNOWN_TEMPLATE_STR
                    template_id = UNKNOWN_TEMPLATE_ID
                    self.unknown_records += 1
        except Exception:
            template = UNKNOWN_TEMPLATE_STR
            template_id = UNKNOWN_TEMPLATE_ID
            self.unknown_records += 1

        return ParsedLogRecord(
            dataset="hdfs",
            line_number=line_number,
            timestamp=epoch_time,
            timestamp_str=full_time_str,
            session_id=block_id,
            log_level=level,
            component=component.strip(),
            raw_message=line,
            template=template,
            template_id=template_id,
            is_anomaly=None,  # HDFS block-level labels resolved via anomaly_label.csv
        )

    def parse_bgl_line(self, line: str, line_number: int) -> ParsedLogRecord:
        """Parse a single raw BGL log record.

        Format: Label Timestamp Date Node Time NodeRepeat Type Component Level Content
        """
        line = line.strip()
        tokens = line.split(maxsplit=9)
        if len(tokens) < 10:
            self.unknown_records += 1
            return ParsedLogRecord(
                dataset="bgl",
                line_number=line_number,
                timestamp=None,
                timestamp_str=None,
                session_id=None,
                log_level=None,
                component=None,
                raw_message=line,
                template=UNKNOWN_TEMPLATE_STR,
                template_id=UNKNOWN_TEMPLATE_ID,
                is_anomaly=None,
            )

        label_token = tokens[0]
        timestamp_raw = tokens[1]
        date_str = tokens[2]
        node = tokens[3]
        time_str = tokens[4]
        node_repeat = tokens[5]
        msg_type = tokens[6]
        component = tokens[7]
        level = tokens[8]
        content = tokens[9]

        is_anomaly = label_token != "-"
        epoch_time = None
        try:
            epoch_time = float(timestamp_raw)
        except ValueError:
            pass

        try:
            if not self.frozen:
                result = self.miner.add_log_message(content)
                template = result.get("template_mined", UNKNOWN_TEMPLATE_STR)
                template_id = int(result.get("cluster_id", UNKNOWN_TEMPLATE_ID))
                self.parsed_records += 1
            else:
                cluster = self.miner.match(content)
                if cluster is not None:
                    template = cluster.get_template()
                    template_id = int(cluster.cluster_id)
                    self.parsed_records += 1
                else:
                    template = UNKNOWN_TEMPLATE_STR
                    template_id = UNKNOWN_TEMPLATE_ID
                    self.unknown_records += 1
        except Exception:
            template = UNKNOWN_TEMPLATE_STR
            template_id = UNKNOWN_TEMPLATE_ID
            self.unknown_records += 1

        return ParsedLogRecord(
            dataset="bgl",
            line_number=line_number,
            timestamp=epoch_time,
            timestamp_str=time_str,
            session_id=node,
            log_level=level,
            component=component,
            raw_message=line,
            template=template,
            template_id=template_id,
            is_anomaly=is_anomaly,
        )

    def parse_line(self, line: str, line_number: int) -> ParsedLogRecord:
        """Parse a single log line according to the configured dataset."""
        self.total_records += 1
        if self.dataset == "hdfs":
            return self.parse_hdfs_line(line, line_number)
        elif self.dataset == "bgl":
            return self.parse_bgl_line(line, line_number)
        else:
            raise ValueError(f"Unsupported dataset for parser: {self.dataset}")

    def parse_stream(self, lines: Iterator[str]) -> Iterator[ParsedLogRecord]:
        """Parse an iterator/stream of log lines."""
        for idx, line in enumerate(lines, start=1):
            if line.strip():
                yield self.parse_line(line, idx)

    def get_stats(self) -> Dict[str, Any]:
        """Return parsing statistics."""
        return {
            "total_records": self.total_records,
            "parsed_records": self.parsed_records,
            "unknown_records": self.unknown_records,
            "unique_templates": len(self.miner.drain.id_to_cluster),
        }

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Return list of all mined templates with cluster IDs and sizes."""
        templates = []
        for cluster_id, cluster in self.miner.drain.id_to_cluster.items():
            templates.append({
                "template_id": cluster_id,
                "template": cluster.get_template(),
                "size": cluster.size,
            })
        return templates

    @staticmethod
    def _extract_hdfs_block_id(text: str) -> Optional[str]:
        """Extract HDFS block ID (e.g., blk_-1608999687919862906)."""
        match = HDFS_BLOCK_ID_REGEX.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _parse_hdfs_timestamp(date_str: str, time_str: str) -> Optional[float]:
        """Parse HDFS timestamp (YYMMDD HHMMSS) into epoch seconds."""
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%y%m%d %H%M%S")
            return dt.timestamp()
        except ValueError:
            return None
