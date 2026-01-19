"""FastAPI application for data execution Glue/EMR MCP server."""

from typing import Any

from fastapi import FastAPI, HTTPException

from data_execution.allowlist import allowlist
from data_execution.aws_emr import emr_client
from data_execution.aws_glue import glue_client
from data_execution.config import config
from data_execution.logging import get_logger
from data_execution.schemas import (
    GetEMRClusterRequest,
    GetEMRStepRequest,
    GetGlueJobRunRequest,
    GetLogGroupsForClusterRequest,
    GetLogGroupsForJobRequest,
    ListEMRStepsRequest,
    ListGlueJobRunsRequest,
    ToolRequest,
    ToolResponse,
)

logger = get_logger(__name__)

app = FastAPI(
    title="Data Execution Glue/EMR MCP Server",
    description="MCP server for AWS Glue and EMR operations",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "data-execution-glue-emr"}


@app.post("/tools", response_model=ToolResponse)
async def call_tool(request: ToolRequest) -> ToolResponse:
    """Handle MCP tool calls.

    Args:
        request: Tool request

    Returns:
        Tool response

    Raises:
        HTTPException: If tool call fails
    """
    tool_name = request.tool
    arguments = request.arguments

    logger.info(f"Tool call: {tool_name} with arguments: {arguments}")

    try:
        if tool_name == "get_glue_job_run":
            return await _handle_get_glue_job_run(arguments)
        elif tool_name == "list_glue_job_runs":
            return await _handle_list_glue_job_runs(arguments)
        elif tool_name == "get_log_groups_for_job":
            return await _handle_get_log_groups_for_job(arguments)
        elif tool_name == "get_emr_step":
            return await _handle_get_emr_step(arguments)
        elif tool_name == "list_emr_steps":
            return await _handle_list_emr_steps(arguments)
        elif tool_name == "get_emr_cluster":
            return await _handle_get_emr_cluster(arguments)
        elif tool_name == "get_log_groups_for_cluster":
            return await _handle_get_log_groups_for_cluster(arguments)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tool: {tool_name}",
            )

    except ValueError as e:
        logger.error(f"Validation error for {tool_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool call failed: {str(e)}")


async def _handle_get_glue_job_run(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_glue_job_run tool call."""
    req = GetGlueJobRunRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_glue_job_allowed(req.job_name):
        raise HTTPException(
            status_code=403,
            detail=f"Glue job not in allowlist: {req.job_name}",
        )

    result = glue_client.get_job_run(
        job_name=req.job_name,
        run_id=req.run_id,
    )

    return ToolResponse(result=result)


async def _handle_list_glue_job_runs(arguments: dict[str, Any]) -> ToolResponse:
    """Handle list_glue_job_runs tool call."""
    req = ListGlueJobRunsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_glue_job_allowed(req.job_name):
        raise HTTPException(
            status_code=403,
            detail=f"Glue job not in allowlist: {req.job_name}",
        )

    result = glue_client.list_job_runs(
        job_name=req.job_name,
        max_results=req.max_results,
        next_token=req.next_token,
    )

    return ToolResponse(result=result)


async def _handle_get_log_groups_for_job(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_log_groups_for_job tool call."""
    req = GetLogGroupsForJobRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_glue_job_allowed(req.job_name):
        raise HTTPException(
            status_code=403,
            detail=f"Glue job not in allowlist: {req.job_name}",
        )

    log_groups = glue_client.get_log_groups_for_job(job_name=req.job_name)

    return ToolResponse(result={"job_name": req.job_name, "log_groups": log_groups})


async def _handle_get_emr_step(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_emr_step tool call."""
    req = GetEMRStepRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_emr_cluster_allowed(req.cluster_id):
        raise HTTPException(
            status_code=403,
            detail=f"EMR cluster not in allowlist: {req.cluster_id}",
        )

    result = emr_client.get_step(
        cluster_id=req.cluster_id,
        step_id=req.step_id,
    )

    return ToolResponse(result=result)


async def _handle_list_emr_steps(arguments: dict[str, Any]) -> ToolResponse:
    """Handle list_emr_steps tool call."""
    req = ListEMRStepsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_emr_cluster_allowed(req.cluster_id):
        raise HTTPException(
            status_code=403,
            detail=f"EMR cluster not in allowlist: {req.cluster_id}",
        )

    result = emr_client.list_steps(
        cluster_id=req.cluster_id,
        step_states=req.step_states,
        max_results=req.max_results,
        marker=req.marker,
    )

    return ToolResponse(result=result)


async def _handle_get_emr_cluster(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_emr_cluster tool call."""
    req = GetEMRClusterRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_emr_cluster_allowed(req.cluster_id):
        raise HTTPException(
            status_code=403,
            detail=f"EMR cluster not in allowlist: {req.cluster_id}",
        )

    result = emr_client.get_cluster(cluster_id=req.cluster_id)

    return ToolResponse(result=result)


async def _handle_get_log_groups_for_cluster(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_log_groups_for_cluster tool call."""
    req = GetLogGroupsForClusterRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_emr_cluster_allowed(req.cluster_id):
        raise HTTPException(
            status_code=403,
            detail=f"EMR cluster not in allowlist: {req.cluster_id}",
        )

    log_groups = emr_client.get_log_groups_for_cluster(cluster_id=req.cluster_id)

    return ToolResponse(result={"cluster_id": req.cluster_id, "log_groups": log_groups})
