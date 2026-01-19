"""Pydantic schemas for MCP tool requests and responses."""

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

class ListExecutionsRequest(BaseModel):
    """Request for list_executions tool."""

    state_machine_arn: str = Field(..., description="State machine ARN")
    status_filter: Optional[str] = Field(
        None, description="Filter by status (RUNNING, SUCCEEDED, FAILED, etc.)"
    )
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    next_token: Optional[str] = Field(None, description="Pagination token")
    region: Optional[str] = Field(
        None, description="AWS region (auto-detected from ARN if not provided)"
    )


class GetExecutionDetailsRequest(BaseModel):
    """Request for get_execution_details tool."""

    execution_arn: str = Field(..., description="Execution ARN")
    region: Optional[str] = Field(
        None, description="AWS region (auto-detected from ARN if not provided)"
    )


class GetExecutionHistoryRequest(BaseModel):
    """Request for get_execution_history tool."""

    execution_arn: str = Field(..., description="Execution ARN")
    max_results: int = Field(default=1000, ge=1, le=10000, description="Maximum events")
    next_token: Optional[str] = Field(None, description="Pagination token")
    reverse_order: bool = Field(default=False, description="Reverse chronological order")
    region: Optional[str] = Field(
        None, description="AWS region (auto-detected from ARN if not provided)"
    )


class StartExecutionRequest(BaseModel):
    """Request for start_execution tool."""

    state_machine_arn: str = Field(..., description="State machine ARN")
    input_data: Optional[dict[str, Any]] = Field(None, description="Execution input")
    name: Optional[str] = Field(None, description="Execution name")
    region: Optional[str] = Field(
        None, description="AWS region (auto-detected from ARN if not provided)"
    )


class StopExecutionRequest(BaseModel):
    """Request for stop_execution tool."""

    execution_arn: str = Field(..., description="Execution ARN")
    error: Optional[str] = Field(None, description="Error code")
    cause: Optional[str] = Field(None, description="Error cause")
    region: Optional[str] = Field(
        None, description="AWS region (auto-detected from ARN if not provided)"
    )
