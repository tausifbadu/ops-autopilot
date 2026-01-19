"""Pydantic schemas for GitHub MCP tool requests and responses."""

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

class SearchCodeRequest(BaseModel):
    """Request for search_code tool."""

    query: str = Field(..., description="Search query")
    repository: str = Field(..., description="Repository name (owner/repo)")
    file_extension: Optional[str] = Field(None, description="Optional file extension filter")


class ReadFileRequest(BaseModel):
    """Request for read_file tool."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    file_path: str = Field(..., description="File path in repository")
    ref: Optional[str] = Field(None, description="Git reference (branch, tag, commit)")


class GetRecentCommitsRequest(BaseModel):
    """Request for get_recent_commits tool."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    file_path: Optional[str] = Field(None, description="Optional file path to filter commits")
    since: Optional[str] = Field(None, description="ISO timestamp to filter commits since")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of commits")


class GetFileBlameRequest(BaseModel):
    """Request for get_file_blame tool."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    file_path: str = Field(..., description="File path")
    ref: Optional[str] = Field(None, description="Git reference (defaults to default branch)")


class CreateBranchRequest(BaseModel):
    """Request for create_branch tool."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    branch_name: str = Field(..., description="New branch name")
    from_ref: str = Field(default="main", description="Base reference")


class CreatePRRequest(BaseModel):
    """Request for create_pr tool."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    title: str = Field(..., description="PR title")
    description: str = Field(..., description="PR description")
    head_branch: str = Field(..., description="Source branch")
    base_branch: str = Field(default="main", description="Target branch")
    files: Optional[list[dict[str, Any]]] = Field(
        None, description="Optional list of file changes"
    )
