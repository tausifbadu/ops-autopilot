"""FastAPI application for orchestration MCP server."""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from orchestration_sfn.allowlist import allowlist
from orchestration_sfn.aws_sfn import sfn_client
from orchestration_sfn.config import config
from orchestration_sfn.logging import get_logger
from orchestration_sfn.schemas import (
    GetExecutionDetailsRequest,
    GetExecutionHistoryRequest,
    ListExecutionsRequest,
    StartExecutionRequest,
    StopExecutionRequest,
    ToolRequest,
    ToolResponse,
)

logger = get_logger(__name__)

app = FastAPI(
    title="Orchestration MCP Server",
    description="MCP server for AWS Step Functions operations",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "orchestration-sfn"}


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
        if tool_name == "list_executions":
            return await _handle_list_executions(arguments)
        elif tool_name == "get_execution_details":
            return await _handle_get_execution_details(arguments)
        elif tool_name == "get_execution_history":
            return await _handle_get_execution_history(arguments)
        elif tool_name == "start_execution":
            return await _handle_start_execution(arguments)
        elif tool_name == "stop_execution":
            return await _handle_stop_execution(arguments)
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


async def _handle_list_executions(arguments: dict[str, Any]) -> ToolResponse:
    """Handle list_executions tool call."""
    req = ListExecutionsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_state_machine_allowed(req.state_machine_arn):
        raise HTTPException(
            status_code=403,
            detail=f"State machine not in allowlist: {req.state_machine_arn}",
        )

    result = sfn_client.list_executions(
        state_machine_arn=req.state_machine_arn,
        status_filter=req.status_filter,
        max_results=req.max_results,
        next_token=req.next_token,
        region=req.region,
    )

    return ToolResponse(result=result)


async def _handle_get_execution_details(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_execution_details tool call."""
    req = GetExecutionDetailsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_execution_allowed(req.execution_arn):
        raise HTTPException(
            status_code=403,
            detail=f"Execution not in allowlist: {req.execution_arn}",
        )

    result = sfn_client.describe_execution(execution_arn=req.execution_arn, region=req.region)

    return ToolResponse(result=result)


async def _handle_get_execution_history(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_execution_history tool call."""
    req = GetExecutionHistoryRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_execution_allowed(req.execution_arn):
        raise HTTPException(
            status_code=403,
            detail=f"Execution not in allowlist: {req.execution_arn}",
        )

    result = sfn_client.get_execution_history(
        execution_arn=req.execution_arn,
        max_results=req.max_results,
        next_token=req.next_token,
        reverse_order=req.reverse_order,
        region=req.region,
    )

    return ToolResponse(result=result)


async def _handle_start_execution(arguments: dict[str, Any]) -> ToolResponse:
    """Handle start_execution tool call."""
    req = StartExecutionRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_state_machine_allowed(req.state_machine_arn):
        raise HTTPException(
            status_code=403,
            detail=f"State machine not in allowlist: {req.state_machine_arn}",
        )

    result = sfn_client.start_execution(
        state_machine_arn=req.state_machine_arn,
        input_data=req.input_data,
        name=req.name,
        region=req.region,
    )

    return ToolResponse(result=result)


async def _handle_stop_execution(arguments: dict[str, Any]) -> ToolResponse:
    """Handle stop_execution tool call."""
    req = StopExecutionRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_execution_allowed(req.execution_arn):
        raise HTTPException(
            status_code=403,
            detail=f"Execution not in allowlist: {req.execution_arn}",
        )

    result = sfn_client.stop_execution(
        execution_arn=req.execution_arn,
        error=req.error,
        cause=req.cause,
        region=req.region,
    )

    return ToolResponse(result=result)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestration_sfn.app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )
