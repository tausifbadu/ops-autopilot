"""Pydantic schemas for CloudWatch observability MCP tool requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    """MCP tool request."""

    tool: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResponse(BaseModel):
    """MCP tool response."""

    result: Any = Field(..., description="Tool result")
    evidence_refs: Optional[list[str]] = Field(
        None, description="S3 references to evidence (if stored)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


# Tool-specific request schemas

class QueryLogsRequest(BaseModel):
    """Request for query_logs tool."""

    log_groups: list[str] = Field(..., description="List of log group names")
    query: str = Field(..., description="CloudWatch Logs Insights query string")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    limit: int = Field(default=1000, ge=1, le=10000, description="Maximum results")


class GetLogEventsRequest(BaseModel):
    """Request for get_log_events tool."""

    log_group: str = Field(..., description="Log group name")
    log_stream: Optional[str] = Field(None, description="Optional log stream name")
    start_time: Optional[datetime] = Field(None, description="Optional start time")
    end_time: Optional[datetime] = Field(None, description="Optional end time")
    limit: int = Field(default=100, ge=1, le=10000, description="Maximum events")
    filter_pattern: Optional[str] = Field(None, description="Optional filter pattern")


class ExtractErrorFingerprintsRequest(BaseModel):
    """Request for extract_error_fingerprints tool."""

    log_events: list[dict[str, Any]] = Field(..., description="List of log event dictionaries")


class GetMetricsRequest(BaseModel):
    """Request for get_metrics tool."""

    namespace: str = Field(..., description="Metric namespace (e.g., AWS/ECS)")
    metric_name: str = Field(..., description="Metric name (e.g., CPUUtilization)")
    dimensions: Optional[list[dict[str, str]]] = Field(
        None, description="Optional metric dimensions"
    )
    start_time: Optional[datetime] = Field(None, description="Start time for metric data")
    end_time: Optional[datetime] = Field(None, description="End time for metric data")
    period: int = Field(default=300, ge=60, description="Period in seconds")
    statistics: Optional[list[str]] = Field(
        default=None, description="List of statistics (Average, Maximum, etc.)"
    )
    unit: Optional[str] = Field(None, description="Optional metric unit")


class ListMetricsRequest(BaseModel):
    """Request for list_metrics tool."""

    namespace: Optional[str] = Field(None, description="Optional namespace filter")
    metric_name: Optional[str] = Field(None, description="Optional metric name filter")
    dimensions: Optional[list[dict[str, str]]] = Field(
        None, description="Optional dimension filters"
    )
