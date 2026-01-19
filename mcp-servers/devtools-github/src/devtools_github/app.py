"""FastAPI application for GitHub MCP server."""

from typing import Any

from fastapi import FastAPI, HTTPException

from devtools_github.allowlist import allowlist
from devtools_github.config import config
from devtools_github.github_client import github_client
from devtools_github.logging import get_logger
from devtools_github.schemas import (
    CreateBranchRequest,
    CreatePRRequest,
    GetFileBlameRequest,
    GetRecentCommitsRequest,
    ReadFileRequest,
    SearchCodeRequest,
    ToolRequest,
    ToolResponse,
)

logger = get_logger(__name__)

app = FastAPI(
    title="GitHub MCP Server",
    description="MCP server for GitHub operations (code search, file reading, PR creation)",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "devtools-github"}


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
        if tool_name == "search_code":
            return await _handle_search_code(arguments)
        elif tool_name == "read_file":
            return await _handle_read_file(arguments)
        elif tool_name == "get_recent_commits":
            return await _handle_get_recent_commits(arguments)
        elif tool_name == "get_file_blame":
            return await _handle_get_file_blame(arguments)
        elif tool_name == "create_branch":
            return await _handle_create_branch(arguments)
        elif tool_name == "create_pr":
            return await _handle_create_pr(arguments)
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


async def _handle_search_code(arguments: dict[str, Any]) -> ToolResponse:
    """Handle search_code tool call."""
    req = SearchCodeRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    result = github_client.search_code(
        query=req.query,
        repository=req.repository,
        file_extension=req.file_extension,
    )

    return ToolResponse(result={"items": result})


async def _handle_read_file(arguments: dict[str, Any]) -> ToolResponse:
    """Handle read_file tool call."""
    req = ReadFileRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    result = github_client.read_file(
        repository=req.repository,
        file_path=req.file_path,
        ref=req.ref,
    )

    return ToolResponse(result=result)


async def _handle_get_recent_commits(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_recent_commits tool call."""
    req = GetRecentCommitsRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    commits = github_client.get_recent_commits(
        repository=req.repository,
        file_path=req.file_path,
        since=req.since,
        limit=req.limit,
    )

    return ToolResponse(result={"commits": commits})


async def _handle_get_file_blame(arguments: dict[str, Any]) -> ToolResponse:
    """Handle get_file_blame tool call."""
    req = GetFileBlameRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    result = github_client.get_file_blame(
        repository=req.repository,
        file_path=req.file_path,
        ref=req.ref,
    )

    return ToolResponse(result=result)


async def _handle_create_branch(arguments: dict[str, Any]) -> ToolResponse:
    """Handle create_branch tool call."""
    req = CreateBranchRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    result = github_client.create_branch(
        repository=req.repository,
        branch_name=req.branch_name,
        from_ref=req.from_ref,
    )

    return ToolResponse(result=result)


async def _handle_create_pr(arguments: dict[str, Any]) -> ToolResponse:
    """Handle create_pr tool call."""
    req = CreatePRRequest(**arguments)
    
    # Validate allowlist
    if not allowlist.is_repository_allowed(req.repository):
        raise HTTPException(
            status_code=403,
            detail=f"Repository not in allowlist: {req.repository}",
        )

    result = github_client.create_pr(
        repository=req.repository,
        title=req.title,
        description=req.description,
        head_branch=req.head_branch,
        base_branch=req.base_branch,
        files=req.files,
    )

    return ToolResponse(result=result)
