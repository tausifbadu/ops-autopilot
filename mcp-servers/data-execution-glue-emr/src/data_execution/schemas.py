"""Pydantic schemas for data execution Glue/EMR MCP tool requests and responses."""

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

class GetGlueJobRunRequest(BaseModel):
    """Request for get_glue_job_run tool."""

    job_name: str = Field(..., description="Glue job name")
    run_id: str = Field(..., description="Job run ID")


class ListGlueJobRunsRequest(BaseModel):
    """Request for list_glue_job_runs tool."""

    job_name: str = Field(..., description="Glue job name")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    next_token: Optional[str] = Field(None, description="Pagination token")


class GetLogGroupsForJobRequest(BaseModel):
    """Request for get_log_groups_for_job tool."""

    job_name: str = Field(..., description="Glue job name")


class GetEMRStepRequest(BaseModel):
    """Request for get_emr_step tool."""

    cluster_id: str = Field(..., description="EMR cluster ID")
    step_id: str = Field(..., description="Step ID")


class ListEMRStepsRequest(BaseModel):
    """Request for list_emr_steps tool."""

    cluster_id: str = Field(..., description="EMR cluster ID")
    step_states: Optional[list[str]] = Field(
        None, description="Optional list of step states to filter"
    )
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    marker: Optional[str] = Field(None, description="Pagination marker")


class GetEMRClusterRequest(BaseModel):
    """Request for get_emr_cluster tool."""

    cluster_id: str = Field(..., description="EMR cluster ID")


class GetLogGroupsForClusterRequest(BaseModel):
    """Request for get_log_groups_for_cluster tool."""

    cluster_id: str = Field(..., description="EMR cluster ID")
