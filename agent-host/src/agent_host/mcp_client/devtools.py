"""GitHub MCP client for code investigation and PR creation."""

from typing import Any, Optional

from agent_host.config import config
from agent_host.logging import get_logger
from agent_host.mcp_client.base import MCPClient, MCPClientConfig

logger = get_logger(__name__)


class GitHubMCPClient:
    """Client for GitHub MCP server."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize GitHub MCP client.

        Args:
            base_url: MCP server base URL (defaults to config)
        """
        self.client = MCPClient(
            MCPClientConfig(
                base_url=base_url or config.mcp_devtools_url or "http://localhost:8007"
            )
        )

    def search_code(
        self, query: str, repository: str, file_extension: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Search code in repository.

        Args:
            query: Search query
            repository: Repository name (owner/repo)
            file_extension: Optional file extension filter

        Returns:
            List of search results
        """
        arguments = {"query": query, "repository": repository}
        if file_extension:
            arguments["file_extension"] = file_extension

        response = self.client.call_tool(tool_name="search_code", arguments=arguments)
        return response.result.get("items", [])

    def read_file(
        self, repository: str, file_path: str, ref: Optional[str] = None
    ) -> dict[str, Any]:
        """Read file from repository.

        Args:
            repository: Repository name (owner/repo)
            file_path: File path in repository
            ref: Git reference (branch, tag, commit) - defaults to default branch

        Returns:
            File contents and metadata
        """
        arguments = {"repository": repository, "file_path": file_path}
        if ref:
            arguments["ref"] = ref

        response = self.client.call_tool(tool_name="read_file", arguments=arguments)
        return response.result

    def get_recent_commits(
        self,
        repository: str,
        file_path: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent commits for repository or file.

        Args:
            repository: Repository name (owner/repo)
            file_path: Optional file path to filter commits
            since: Optional ISO timestamp to filter commits since
            limit: Maximum number of commits

        Returns:
            List of commits
        """
        arguments = {"repository": repository, "limit": limit}
        if file_path:
            arguments["file_path"] = file_path
        if since:
            arguments["since"] = since

        response = self.client.call_tool(tool_name="get_recent_commits", arguments=arguments)
        return response.result.get("commits", [])

    def get_file_blame(
        self, repository: str, file_path: str, ref: Optional[str] = None
    ) -> dict[str, Any]:
        """Get git blame for file.

        Args:
            repository: Repository name (owner/repo)
            file_path: File path
            ref: Git reference (defaults to default branch)

        Returns:
            Blame information
        """
        arguments = {"repository": repository, "file_path": file_path}
        if ref:
            arguments["ref"] = ref

        response = self.client.call_tool(tool_name="get_file_blame", arguments=arguments)
        return response.result

    def create_branch(
        self, repository: str, branch_name: str, from_ref: str = "main"
    ) -> dict[str, Any]:
        """Create a new branch.

        Args:
            repository: Repository name (owner/repo)
            branch_name: New branch name
            from_ref: Base reference (default: main)

        Returns:
            Branch creation result
        """
        response = self.client.call_tool(
            tool_name="create_branch",
            arguments={
                "repository": repository,
                "branch_name": branch_name,
                "from_ref": from_ref,
            },
        )
        return response.result

    def create_pr(
        self,
        repository: str,
        title: str,
        description: str,
        head_branch: str,
        base_branch: str = "main",
        files: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            repository: Repository name (owner/repo)
            title: PR title
            description: PR description
            head_branch: Source branch
            base_branch: Target branch (default: main)
            files: Optional list of file changes

        Returns:
            PR creation result with PR URL
        """
        arguments = {
            "repository": repository,
            "title": title,
            "description": description,
            "head_branch": head_branch,
            "base_branch": base_branch,
        }
        if files:
            arguments["files"] = files

        response = self.client.call_tool(tool_name="create_pr", arguments=arguments)
        return response.result
