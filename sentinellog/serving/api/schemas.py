"""Typed Pydantic request and response schemas for SentinelLog API."""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sentinellog.serving.version import API_VERSION, SERVING_VERSION

# Label leakage guard forbidden keys
FORBIDDEN_LABEL_KEYS = {
    "anomaly_label",
    "ground_truth",
    "is_anomaly",
    "label",
    "target",
    "actual_label",
    "test_label",
}

# Path traversal detection pattern
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.[/\\])|([a-zA-Z]:[/\\])|(^[/\\](etc|sys|proc|var|usr|bin|root))")


class HealthLiveResponse(BaseModel):
    """Liveness probe response."""

    model_config = ConfigDict(extra="forbid")
    status: str = Field(default="ok", description="Process liveness status.")


class HealthReadyResponse(BaseModel):
    """Readiness probe response."""

    model_config = ConfigDict(extra="forbid")
    status: str = Field(..., description="Service readiness state ('ready' or 'not_ready').")
    checks: Dict[str, str] = Field(..., description="Individual dependency health states.")


class RootMetadataResponse(BaseModel):
    """Root API service metadata response."""

    model_config = ConfigDict(extra="forbid")
    service_name: str = Field(default="SentinelLog", description="Name of the service.")
    api_version: str = Field(default=API_VERSION, description="Active API version.")
    app_version: str = Field(default=SERVING_VERSION, description="Application build version.")
    status: str = Field(default="operational", description="Current service operational status.")


class AnalysisOptions(BaseModel):
    """Optional analysis execution parameters."""

    model_config = ConfigDict(extra="forbid")

    window_id: Optional[str] = Field(
        default=None,
        description="Optional identifier of an evaluated calibration query window.",
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to include resolved citations in the response.",
    )
    include_raw_excerpts: bool = Field(
        default=False,
        description="Whether to include bounded citation text in the response.",
    )


class AnalyzeRequest(BaseModel):
    """Request payload for bounded system log analysis."""

    model_config = ConfigDict(extra="forbid")

    dataset: Literal["hdfs", "bgl"] = Field(
        ...,
        description="Target dataset identifier (strictly 'hdfs' or 'bgl').",
    )
    logs: List[str] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Non-empty sequence of raw log lines (max 500 records).",
    )
    options: Optional[AnalysisOptions] = Field(
        default=None,
        description="Optional execution configuration.",
    )

    @field_validator("logs")
    @classmethod
    def validate_logs_content(cls, lines: List[str]) -> List[str]:
        """Validate log record lengths and check for prohibited path traversal."""
        if not lines:
            raise ValueError("Log sequence must not be empty.")

        for idx, line in enumerate(lines):
            if len(line) > 4096:
                raise ValueError(f"Log line at index {idx} exceeds maximum allowed length of 4096 characters.")
            if PATH_TRAVERSAL_PATTERN.search(line):
                raise ValueError(f"Log line at index {idx} contains forbidden filesystem path references.")

        return lines

    @model_validator(mode="before")
    @classmethod
    def guard_label_leakage(cls, data: Any) -> Any:
        """Prevent client injection of ground truth anomaly labels."""
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_LABEL_KEYS:
                    raise ValueError(f"Label leakage rejected: '{k}' is a forbidden ground truth field.")
        return data


class ClaimResponse(BaseModel):
    """Structured claim produced by explanation layer."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_type: str
    text: str
    citation_ids: List[str] = Field(default_factory=list)
    supported: bool
    support_score: float = Field(default=0.0)


class CitationResponse(BaseModel):
    """Source-addressable citation metadata with safe relative coordinates."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str
    dataset: str
    split: str
    source_window_id: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    citation_text: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Standardized response schema for incident analysis."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="Unique request tracing identifier.")
    status: str = Field(..., description="Analysis status ('success', 'abstention', 'error').")
    dataset: str = Field(..., description="Dataset name.")
    decision: str = Field(..., description="Deterministic Phase 8 decision.")
    severity: str = Field(..., description="Deterministic Phase 8 severity.")
    confidence: float = Field(..., description="Reasoning confidence score [0.0, 1.0].")
    explanation_status: str = Field(..., description="Phase 9 explanation status.")
    summary: Optional[str] = Field(default=None, description="Executive explanation summary.")
    explanation: Optional[str] = Field(default=None, description="Detailed grounded explanation.")
    claims: List[ClaimResponse] = Field(default_factory=list, description="Structured claims.")
    citations: List[CitationResponse] = Field(default_factory=list, description="Supporting citations.")
    evidence_sufficiency: str = Field(..., description="Evidence sufficiency evaluation.")
    provenance_status: str = Field(..., description="Evidence provenance verification status.")
    faithfulness_status: str = Field(..., description="Claim faithfulness evaluation status.")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe processing telemetry.")


class ErrorDetail(BaseModel):
    """Structured error information."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standardized error envelope."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
