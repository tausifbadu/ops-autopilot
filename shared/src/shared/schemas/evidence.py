"""Evidence pack structure for storing collected evidence."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from .common import S3Reference


class LogEntry(BaseModel):
    """Single log entry."""
    
    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level (INFO, ERROR, WARN, etc.)")
    message: str = Field(..., description="Log message")
    source: Optional[str] = Field(None, description="Log source (service, job, etc.)")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional log metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogEvidence(BaseModel):
    """Evidence from log queries."""
    
    log_group: str = Field(..., description="CloudWatch log group name")
    query: Optional[str] = Field(None, description="Query used to fetch logs")
    time_range_start: datetime = Field(..., description="Query start time")
    time_range_end: datetime = Field(..., description="Query end time")
    entries: list[LogEntry] = Field(default_factory=list, description="Log entries")
    error_fingerprints: Optional[list[str]] = Field(None, description="Extracted error fingerprints")
    s3_reference: Optional[S3Reference] = Field(None, description="S3 reference if logs stored separately")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricDataPoint(BaseModel):
    """Single metric data point."""
    
    timestamp: datetime = Field(..., description="Metric timestamp")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricEvidence(BaseModel):
    """Evidence from metric queries."""
    
    metric_name: str = Field(..., description="CloudWatch metric name")
    namespace: str = Field(..., description="Metric namespace")
    dimensions: dict[str, str] = Field(default_factory=dict, description="Metric dimensions")
    time_range_start: datetime = Field(..., description="Query start time")
    time_range_end: datetime = Field(..., description="Query end time")
    data_points: list[MetricDataPoint] = Field(default_factory=list, description="Metric data points")
    statistics: Optional[dict[str, float]] = Field(None, description="Computed statistics (min, max, avg, p95, p99)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionDetails(BaseModel):
    """Step Functions execution details."""
    
    execution_arn: str = Field(..., description="Execution ARN")
    state_machine_arn: str = Field(..., description="State machine ARN")
    status: str = Field(..., description="Execution status")
    start_date: datetime = Field(..., description="Start time")
    stop_date: Optional[datetime] = Field(None, description="Stop time")
    input: Optional[dict[str, Any]] = Field(None, description="Execution input")
    output: Optional[dict[str, Any]] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message")
    cause: Optional[str] = Field(None, description="Failure cause")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionHistory(BaseModel):
    """Step Functions execution history."""
    
    execution_arn: str = Field(..., description="Execution ARN")
    events: list[dict[str, Any]] = Field(default_factory=list, description="Execution events")
    failing_state: Optional[str] = Field(None, description="State that failed")
    state_transitions: Optional[list[dict[str, Any]]] = Field(None, description="State transitions")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GlueJobRunDetails(BaseModel):
    """Glue job run details."""
    
    job_name: str = Field(..., description="Glue job name")
    job_run_id: str = Field(..., description="Job run ID")
    status: str = Field(..., description="Job run status")
    started_on: Optional[datetime] = Field(None, description="Start time")
    completed_on: Optional[datetime] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error message")
    allocated_capacity: Optional[int] = Field(None, description="Allocated DPUs")
    execution_time: Optional[int] = Field(None, description="Execution time in seconds")
    log_group: Optional[str] = Field(None, description="CloudWatch log group")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EMRStepDetails(BaseModel):
    """EMR step details."""
    
    cluster_id: str = Field(..., description="EMR cluster ID")
    step_id: str = Field(..., description="Step ID")
    name: str = Field(..., description="Step name")
    status: str = Field(..., description="Step status")
    start_datetime: Optional[datetime] = Field(None, description="Start time")
    end_datetime: Optional[datetime] = Field(None, description="End time")
    failure_details: Optional[dict[str, Any]] = Field(None, description="Failure details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ECSServiceDetails(BaseModel):
    """ECS service details."""
    
    service_name: str = Field(..., description="Service name")
    cluster_name: str = Field(..., description="Cluster name")
    status: str = Field(..., description="Service status")
    desired_count: int = Field(..., description="Desired task count")
    running_count: int = Field(..., description="Running task count")
    pending_count: int = Field(..., description="Pending task count")
    deployments: list[dict[str, Any]] = Field(default_factory=list, description="Recent deployments")
    task_definitions: Optional[list[str]] = Field(None, description="Task definition ARNs")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ECSTaskDetails(BaseModel):
    """ECS task details."""
    
    task_arn: str = Field(..., description="Task ARN")
    task_definition_arn: str = Field(..., description="Task definition ARN")
    last_status: str = Field(..., description="Last status")
    stopped_reason: Optional[str] = Field(None, description="Stopped reason")
    stopped_at: Optional[datetime] = Field(None, description="Stopped time")
    started_at: Optional[datetime] = Field(None, description="Started time")
    cpu: Optional[str] = Field(None, description="CPU allocation")
    memory: Optional[str] = Field(None, description="Memory allocation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataQualityCheckResult(BaseModel):
    """Data quality check result."""
    
    dataset_id: str = Field(..., description="Dataset identifier")
    partition: Optional[str] = Field(None, description="Partition checked")
    rule_name: str = Field(..., description="DQ rule name")
    status: str = Field(..., description="Check status (PASS, FAIL, WARN)")
    expected_value: Optional[Any] = Field(None, description="Expected value")
    actual_value: Optional[Any] = Field(None, description="Actual value")
    threshold: Optional[float] = Field(None, description="Threshold used")
    severity: Optional[str] = Field(None, description="Severity if failed")
    message: Optional[str] = Field(None, description="Check message")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EvidencePack(BaseModel):
    """Complete evidence pack containing all collected evidence."""
    
    incident_id: str = Field(..., description="Incident ID this evidence belongs to")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="When evidence was collected")
    collector: str = Field(..., description="Who/what collected this evidence (agent name)")
    
    # Execution evidence
    execution_details: Optional[ExecutionDetails] = Field(None, description="Step Functions execution details")
    execution_history: Optional[ExecutionHistory] = Field(None, description="Step Functions execution history")
    glue_job_run: Optional[GlueJobRunDetails] = Field(None, description="Glue job run details")
    emr_step: Optional[EMRStepDetails] = Field(None, description="EMR step details")
    
    # Observability evidence
    logs: list[LogEvidence] = Field(default_factory=list, description="Log evidence")
    metrics: list[MetricEvidence] = Field(default_factory=list, description="Metric evidence")
    
    # Runtime evidence
    ecs_service: Optional[ECSServiceDetails] = Field(None, description="ECS service details")
    ecs_tasks: list[ECSTaskDetails] = Field(default_factory=list, description="ECS task details")
    
    # Data quality evidence
    dq_checks: list[DataQualityCheckResult] = Field(default_factory=list, description="Data quality check results")
    
    # Additional evidence
    additional_data: dict[str, Any] = Field(default_factory=dict, description="Additional evidence data")
    
    # Storage reference
    s3_reference: Optional[S3Reference] = Field(None, description="S3 location where full evidence is stored")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
