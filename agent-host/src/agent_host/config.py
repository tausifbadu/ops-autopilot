"""Configuration for Agent Host - supports both local and AWS environments."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Agent Host configuration."""

    # Environment detection
    environment: str = Field(
        default="local",
        description="Environment: 'local' or 'aws' (auto-detected)",
    )
    
    # AWS settings
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # MCP Server URLs (auto-configured based on environment)
    mcp_orchestration_url: str = Field(
        default="http://localhost:8001",
        description="Orchestration MCP server URL",
    )
    mcp_observability_url: str = Field(
        default="http://localhost:8002",
        description="Observability MCP server URL",
    )
    mcp_data_execution_url: Optional[str] = Field(
        None, description="Data execution MCP server URL"
    )
    mcp_runtime_url: Optional[str] = Field(None, description="Runtime MCP server URL")
    mcp_data_quality_url: Optional[str] = Field(
        None, description="Data quality MCP server URL"
    )
    mcp_finops_url: Optional[str] = Field(None, description="FinOps MCP server URL")
    mcp_devtools_url: Optional[str] = Field(None, description="DevTools MCP server URL")
    mcp_chatops_url: Optional[str] = Field(None, description="ChatOps MCP server URL")
    
    # SQS Configuration (AWS mode)
    sqs_queue_incidents: Optional[str] = Field(
        None, description="SQS queue URL for incidents"
    )
    sqs_queue_dq: Optional[str] = Field(None, description="SQS queue URL for DQ checks")
    sqs_queue_cost: Optional[str] = Field(None, description="SQS queue URL for cost scan")
    sqs_queue_daily: Optional[str] = Field(
        None, description="SQS queue URL for daily sweep"
    )
    
    # DynamoDB Configuration (AWS mode)
    dynamodb_registry_table: Optional[str] = Field(
        None, description="DynamoDB table name for workflow registry"
    )
    dynamodb_incidents_table: Optional[str] = Field(
        None, description="DynamoDB table name for incidents"
    )
    dynamodb_baselines_table: Optional[str] = Field(
        None, description="DynamoDB table name for baselines"
    )
    
    # S3 Configuration (AWS mode)
    s3_evidence_bucket: Optional[str] = Field(
        None, description="S3 bucket name for evidence storage"
    )
    
    # Local mode settings
    local_evidence_dir: str = Field(
        default="./evidence", description="Local directory for evidence storage"
    )
    local_mode: bool = Field(
        default=False, description="Run in local mode (no SQS polling)"
    )
    local_event_file: Optional[str] = Field(
        None, description="Local event file to process (local mode only)"
    )
    
    # LLM Configuration
    llm_provider: str = Field(
        default="bedrock",
        description="LLM provider: bedrock, openai, anthropic, gemini",
    )
    llm_api_key: Optional[str] = Field(None, description="LLM API key (if needed)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.
        
        Automatically detects if running in AWS (ECS) or locally:
        - AWS: Checks for ECS metadata endpoint or ENVIRONMENT variable
        - Local: Uses localhost URLs and local file storage
        """
        # Detect environment
        environment = os.getenv("ENVIRONMENT", "local")
        
        # Check if running in ECS (AWS)
        is_aws = (
            environment != "local"
            or os.getenv("ECS_CONTAINER_METADATA_URI_V4") is not None
            or os.getenv("AWS_EXECUTION_ENV") is not None
        )
        
        if is_aws:
            # AWS/ECS Configuration
            return cls(
                environment=environment,
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
                # MCP servers use service discovery in AWS
                mcp_orchestration_url=os.getenv(
                    "MCP_ORCHESTRATION_URL",
                    "http://mcp-orchestration-sfn:8001",
                ),
                mcp_observability_url=os.getenv(
                    "MCP_OBSERVABILITY_URL",
                    "http://mcp-observability-cloudwatch:8002",
                ),
                mcp_data_execution_url=os.getenv(
                    "MCP_DATA_EXECUTION_URL",
                    "http://mcp-data-execution-glue-emr:8003",
                ),
                mcp_runtime_url=os.getenv(
                    "MCP_RUNTIME_URL", "http://mcp-runtime-ecs:8004"
                ),
                mcp_data_quality_url=os.getenv(
                    "MCP_DATA_QUALITY_URL", "http://mcp-data-quality-athena:8005"
                ),
                mcp_finops_url=os.getenv("MCP_FINOPS_URL", "http://mcp-finops:8006"),
                mcp_devtools_url=os.getenv(
                    "MCP_DEVTOOLS_URL", "http://mcp-devtools-github:8007"
                ),
                mcp_chatops_url=os.getenv(
                    "MCP_CHATOPS_URL", "http://mcp-chatops:8008"
                ),
                # SQS queues
                sqs_queue_incidents=os.getenv("SQS_QUEUE_INCIDENTS"),
                sqs_queue_dq=os.getenv("SQS_QUEUE_DQ"),
                sqs_queue_cost=os.getenv("SQS_QUEUE_COST"),
                sqs_queue_daily=os.getenv("SQS_QUEUE_DAILY"),
                # DynamoDB tables
                dynamodb_registry_table=os.getenv("DYNAMODB_REGISTRY"),
                dynamodb_incidents_table=os.getenv("DYNAMODB_INCIDENTS"),
                dynamodb_baselines_table=os.getenv("DYNAMODB_BASELINES"),
                # S3 bucket
                s3_evidence_bucket=os.getenv("S3_EVIDENCE_BUCKET"),
                # LLM
                llm_provider=os.getenv("LLM_PROVIDER", "bedrock"),
                llm_api_key=os.getenv("LLM_API_KEY"),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                local_mode=False,
            )
        else:
            # Local Development Configuration
            return cls(
                environment="local",
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
                # MCP servers on localhost (from docker-compose)
                mcp_orchestration_url=os.getenv(
                    "MCP_ORCHESTRATION_URL", "http://localhost:8001"
                ),
                mcp_observability_url=os.getenv(
                    "MCP_OBSERVABILITY_URL", "http://localhost:8002"
                ),
                mcp_data_execution_url=os.getenv(
                    "MCP_DATA_EXECUTION_URL", "http://localhost:8003"
                ),
                mcp_runtime_url=os.getenv("MCP_RUNTIME_URL", "http://localhost:8004"),
                mcp_data_quality_url=os.getenv(
                    "MCP_DATA_QUALITY_URL", "http://localhost:8005"
                ),
                mcp_finops_url=os.getenv("MCP_FINOPS_URL", "http://localhost:8006"),
                mcp_devtools_url=os.getenv(
                    "MCP_DEVTOOLS_URL", "http://localhost:8007"
                ),
                mcp_chatops_url=os.getenv("MCP_CHATOPS_URL", "http://localhost:8008"),
                # Local storage
                local_evidence_dir=os.getenv("LOCAL_EVIDENCE_DIR", "./evidence"),
                local_mode=True,
                local_event_file=os.getenv("LOCAL_EVENT_FILE"),
                # LLM (can use same providers locally)
                llm_provider=os.getenv("LLM_PROVIDER", "openai"),  # Default to OpenAI for local
                llm_api_key=os.getenv("LLM_API_KEY"),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
            )

    def is_aws_mode(self) -> bool:
        """Check if running in AWS mode."""
        return not self.local_mode

    def is_local_mode(self) -> bool:
        """Check if running in local mode."""
        return self.local_mode


# Global config instance
config = Config.from_env()
