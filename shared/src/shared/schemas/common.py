"""Common types and base models used across all schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Timestamp(BaseModel):
    """ISO 8601 timestamp with timezone."""
    
    value: datetime = Field(..., description="ISO 8601 timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IncidentID(BaseModel):
    """Unique identifier for an incident."""
    
    value: str = Field(..., description="Unique incident identifier")
    
    @classmethod
    def generate(cls) -> "IncidentID":
        """Generate a new incident ID."""
        return cls(value=f"incident_{uuid4().hex[:16]}")


class ExecutionARN(BaseModel):
    """AWS Step Functions execution ARN."""
    
    value: str = Field(..., description="Step Functions execution ARN", pattern=r"^arn:aws:states:.*")
    
    def __str__(self) -> str:
        return self.value


class StateMachineARN(BaseModel):
    """AWS Step Functions state machine ARN."""
    
    value: str = Field(..., description="Step Functions state machine ARN", pattern=r"^arn:aws:states:.*")
    
    def __str__(self) -> str:
        return self.value


class Tier(str, Enum):
    """Environment tier."""
    
    PROD = "prod"
    NONPROD = "nonprod"
    DEV = "dev"


class Severity(str, Enum):
    """Incident severity level."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(str, Enum):
    """Generic status enum."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    RUNNING = "running"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class Confidence(BaseModel):
    """Confidence score between 0.0 and 1.0."""
    
    value: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    
    def __float__(self) -> float:
        return self.value


class S3Reference(BaseModel):
    """Reference to an S3 object."""
    
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key")
    
    def to_uri(self) -> str:
        """Convert to S3 URI."""
        return f"s3://{self.bucket}/{self.key}"
    
    @classmethod
    def from_uri(cls, uri: str) -> "S3Reference":
        """Parse from S3 URI."""
        if not uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {uri}")
        parts = uri[5:].split("/", 1)
        return cls(bucket=parts[0], key=parts[1] if len(parts) > 1 else "")


class WorkflowMetadata(BaseModel):
    """Metadata about a workflow."""
    
    name: str = Field(..., description="Workflow name")
    owner: Optional[str] = Field(None, description="Workflow owner/team")
    tier: Tier = Field(..., description="Environment tier")
    state_machine_arn: Optional[StateMachineARN] = Field(None, description="Step Functions state machine ARN")
    criticality: Optional[str] = Field(None, description="Criticality level")
    sla_minutes: Optional[int] = Field(None, description="SLA in minutes", ge=0)
    outputs: Optional[list[str]] = Field(None, description="Output datasets")


class BaseEvent(BaseModel):
    """Base class for all events."""
    
    event_id: str = Field(default_factory=lambda: f"event_{uuid4().hex[:16]}", description="Unique event ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    event_type: str = Field(..., description="Event type")
    source: Optional[str] = Field(None, description="Event source")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
