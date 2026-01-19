"""Configuration for orchestration MCP server."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Server configuration."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8001, description="Server port")
    
    # AWS settings
    aws_region: str = Field(
        default="us-east-1",
        description="Default AWS region (region is auto-detected from ARNs if not provided)",
    )
    aws_endpoint_url: Optional[str] = Field(
        None, description="AWS endpoint URL (for local testing)"
    )
    
    # Allowlist settings
    allowlist_enabled: bool = Field(
        default=True, description="Enable resource allowlist validation"
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
            port=int(os.getenv("PORT", "8001")),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
            allowlist_enabled=os.getenv("ALLOWLIST_ENABLED", "true").lower() == "true",
            allowlist_file=os.getenv("ALLOWLIST_FILE"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global config instance
config = Config.from_env()
