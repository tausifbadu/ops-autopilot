"""GitHub API client wrapper."""

from datetime import datetime
from typing import Any, Optional

import httpx

from devtools_github.config import config
from devtools_github.logging import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Wrapper for GitHub API with authentication and error handling."""

    def __init__(
        self,
        token: Optional[str] = None,
        api_url: str = "https://api.github.com",
    ):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            api_url: GitHub API base URL
        """
        self.token = token or config.github_token
        self.api_url = api_url.rstrip("/")
        self.base_url = f"{self.api_url}"

        if not self.token:
            logger.warning("No GitHub token provided - API calls may fail")

        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ops-autopilot-mcp-server",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to GitHub API.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body data (for POST/PATCH)

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"GitHub API {method} {url}")

        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

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
        owner, repo = repository.split("/", 1)
        search_query = f"{query} repo:{owner}/{repo}"
        if file_extension:
            search_query += f" extension:{file_extension}"

        try:
            response = self._request(
                "GET",
                "/search/code",
                params={"q": search_query, "per_page": 100},
            )
            items = response.get("items", [])
            logger.info(f"Found {len(items)} code search results for '{query}' in {repository}")
            return items
        except httpx.HTTPError as e:
            logger.error(f"Code search failed: {e}")
            raise

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
        owner, repo = repository.split("/", 1)
        endpoint = f"/repos/{owner}/{repo}/contents/{file_path}"
        params = {}
        if ref:
            params["ref"] = ref

        try:
            response = self._request("GET", endpoint, params=params if params else None)
            
            # Decode base64 content if present
            content = response.get("content", "")
            if content and response.get("encoding") == "base64":
                import base64
                content = base64.b64decode(content).decode("utf-8")
                response["content"] = content

            logger.info(f"Read file {file_path} from {repository}")
            return response
        except httpx.HTTPError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

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
        owner, repo = repository.split("/", 1)
        endpoint = f"/repos/{owner}/{repo}/commits"
        params = {"per_page": min(limit, 100)}
        if since:
            params["since"] = since
        if file_path:
            params["path"] = file_path

        try:
            response = self._request("GET", endpoint, params=params)
            # GitHub API returns a list directly for commits endpoint
            commits = response if isinstance(response, list) else []
            commits = commits[:limit]  # Limit results
            logger.info(f"Retrieved {len(commits)} commits from {repository}")
            return commits
        except httpx.HTTPError as e:
            logger.error(f"Failed to get commits: {e}")
            raise

    def get_file_blame(
        self, repository: str, file_path: str, ref: Optional[str] = None
    ) -> dict[str, Any]:
        """Get git blame for file.

        Args:
            repository: Repository name (owner/repo)
            file_path: File path
            ref: Git reference (defaults to default branch)

        Returns:
            Blame information with recent changes
        """
        owner, repo = repository.split("/", 1)
        endpoint = f"/repos/{owner}/{repo}/commits"
        params = {"path": file_path, "per_page": 20}
        if ref:
            params["sha"] = ref

        try:
            commits = self._request("GET", endpoint, params=params)
            # GitHub API returns a list directly for commits endpoint
            commits_list = commits if isinstance(commits, list) else []
            
            # Extract recent changes from commits
            recent_changes = []
            for commit in commits_list[:10]:  # Last 10 commits
                if isinstance(commit, dict):
                    recent_changes.append({
                        "sha": commit.get("sha", "")[:7],
                        "message": commit.get("commit", {}).get("message", "").split("\n")[0],
                        "author": commit.get("commit", {}).get("author", {}).get("name", ""),
                        "date": commit.get("commit", {}).get("author", {}).get("date", ""),
                    })

            logger.info(f"Retrieved blame info for {file_path} from {repository}")
            return {
                "file_path": file_path,
                "recent_changes": recent_changes,
                "total_commits": len(commits_list),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to get blame: {e}")
            raise

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
        owner, repo = repository.split("/", 1)
        
        # First, get the SHA of the base ref
        ref_endpoint = f"/repos/{owner}/{repo}/git/ref/heads/{from_ref}"
        try:
            ref_response = self._request("GET", ref_endpoint)
            sha = ref_response["object"]["sha"]
        except httpx.HTTPError as e:
            logger.error(f"Failed to get base ref {from_ref}: {e}")
            raise

        # Create new branch
        create_endpoint = f"/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha,
        }

        try:
            response = self._request("POST", create_endpoint, json_data=payload)
            logger.info(f"Created branch {branch_name} in {repository}")
            return response
        except httpx.HTTPError as e:
            logger.error(f"Failed to create branch: {e}")
            raise

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

        Note: This creates the PR but doesn't commit files.
        Files should be committed separately using the GitHub API or git.

        Args:
            repository: Repository name (owner/repo)
            title: PR title
            description: PR description
            head_branch: Source branch
            base_branch: Target branch (default: main)
            files: Optional list of file changes (not implemented in MVP)

        Returns:
            PR creation result with PR URL
        """
        owner, repo = repository.split("/", 1)
        endpoint = f"/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "body": description,
            "head": head_branch,
            "base": base_branch,
        }

        try:
            response = self._request("POST", endpoint, json_data=payload)
            pr_url = response.get("html_url", "")
            logger.info(f"Created PR #{response.get('number')} in {repository}: {pr_url}")
            return {
                "pr_number": response.get("number"),
                "pr_url": pr_url,
                "state": response.get("state"),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to create PR: {e}")
            raise


# Global GitHub client instance
github_client = GitHubClient()
