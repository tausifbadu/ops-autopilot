"""FastAPI application for observability CloudWatch MCP server."""

from typing import Any

from fastapi import FastAPI, HTTPException

from observability_cloudwatch.allowlist import allowlist
from observability_cloudwatch.aws_logs import logs_client
from observability_cloudwatch.aws_metrics import metrics_client
from observability_cloudwatch.config import config
from observability_cloudwatch.logging import get_logger
from observability_cloudwatch.schemas import (
    ExtractErrorFingerprintsRequest,
    GetLogEventsRequest,
    GetMetricsRequest,
    ListMetricsRequest,
    QueryLogsRequest,
    ToolRequest,
    ToolResponse,
)

logger = get_logger(__name__)

app = FastAPI(
    title="Observability CloudWatch MCP Server",
    description="MCP server for CloudWatch Logs and Metrics operations",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "observability-cloudwatch"}


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
        if tool_name == "query_logs":
            return await _handle_query_logs(arguments)
        elif tool_name == "get_log_events":
            return await _handle_get_log_events(arguments)
        elif tool_name == "extract_error_fingerprints":
            return await _handle_extract_error_fingerprints(arguments)
        elif tool_name == "get_metrics":
            return await _handle_get_metrics(arguments)
        elif tool_name == "list_metrics":
            return await _handle_list_metrics(arguments)
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


async def _handle_query_logs(arguments: dict[str, Any]) -> ToolResponse:
    """Handle query_logs tool call."""
    req = QueryLogsRequest(**arguments)
    
    # Validate allowlist for all log groups
    for log_group in req.log_groups:
        if not allowlist.is_log_group_allowed(log_group):
            raise HTTPException(
                status_code=403,
                detail=f"Log group not in allowlist: {log_group}",
            )

    result = logs_client.query_logs_insights(
        log_groups=req.log_groups,
        query=req.query,
        start_time=req.start_time,
        end_time=req.end_time,
        limit=req.limit,
    )

    return ToolResponse(result=result)


async def _handle_get_log_events(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_log_events tool call."""
    req = GetLogEventsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_log_group_allowed(req.log_group):
        raise HTTPException(
            status_code=403,
            detail=f"Log group not in allowlist: {req.log_group}",
        )

    result = logs_client.get_log_events(
        log_group=req.log_group,
        log_stream=req.log_stream,
        start_time=req.start_time,
        end_time=req.end_time,
        limit=req.limit,
        filter_pattern=req.filter_pattern,
    )

    return ToolResponse(result=result)


async def _handle_extract_error_fingerprints(arguments: dict[str, Any]) -> ToolResponse:
    """Handle extract_error_fingerprints tool call."""
    req = ExtractErrorFingerprintsRequest(**arguments)

    fingerprints = logs_client.extract_error_fingerprints(req.log_events)

    return ToolResponse(result={"fingerprints": fingerprints})


async def _handle_get_metrics(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_metrics tool call."""
    req = GetMetricsRequest(**arguments)

    result = metrics_client.get_metric_statistics(
        namespace=req.namespace,
        metric_name=req.metric_name,
        dimensions=req.dimensions,
        start_time=req.start_time,
        end_time=req.end_time,
        period=req.period,
        statistics=req.statistics,
        unit=req.unit,
    )

    return ToolResponse(result=result)


async def _handle_list_metrics(arguments: dict[str, Any]) -> ToolResponse:
    """Handle list_metrics tool call."""
    req = ListMetricsRequest(**arguments)

    metrics = metrics_client.list_metrics(
        namespace=req.namespace,
        metric_name=req.metric_name,
        dimensions=req.dimensions,
    )

    return ToolResponse(result={"metrics": metrics})
