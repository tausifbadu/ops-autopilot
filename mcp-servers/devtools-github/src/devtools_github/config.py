"""Configuration for GitHub MCP server."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Server configuration."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8007, description="Server port")
    
    # GitHub settings
    github_token: Optional[str] = Field(
        None, description="GitHub personal access token (required)"
    )
    github_api_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL (for GitHub Enterprise)",
    )
    
    # Allowlist settings
    allowlist_enabled: bool = Field(
        default=True, description="Enable repository allowlist validation"
    )
    allowlist_file: Optional[str] = Field(
        None, description="Path to allowlist file (optional)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8007")),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            allowlist_enabled=os.getenv("ALLOWLIST_ENABLED", "true").lower() == "true",
            allowlist_file=os.getenv("ALLOWLIST_FILE"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global config instance
config = Config.from_env()
