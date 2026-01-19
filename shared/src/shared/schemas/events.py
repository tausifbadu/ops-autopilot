"""Event types for the ops-autopilot system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .common import BaseEvent, ExecutionARN, StateMachineARN, Tier


class EventType(str, Enum):
    """Event type enumeration."""
    
    PIPELINE_FAILURE = "PIPELINE_FAILURE"
    API_FAILURE = "API_FAILURE"
    DQ_CHECK_REQUEST = "DQ_CHECK_REQUEST"
    DQ_SCHEDULED_CHECK = "DQ_SCHEDULED_CHECK"
    DAILY_SWEEP = "DAILY_SWEEP"
    COST_DAILY_SCAN = "COST_DAILY_SCAN"
    COST_WEEKLY_REVIEW = "COST_WEEKLY_REVIEW"
    PIPELINE_SLA_CHECK = "PIPELINE_SLA_CHECK"


class PipelineFailureEvent(BaseEvent):
    """Pipeline failure event from Step Functions/Glue/EMR."""
    
    event_type: EventType = Field(default=EventType.PIPELINE_FAILURE, description="Event type")
    execution_arn: Optional[ExecutionARN] = Field(None, description="Step Functions execution ARN")
    state_machine_arn: Optional[StateMachineARN] = Field(None, description="Step Functions state machine ARN")
    glue_job_name: Optional[str] = Field(None, description="Glue job name")
    glue_job_run_id: Optional[str] = Field(None, description="Glue job run ID")
    emr_cluster_id: Optional[str] = Field(None, description="EMR cluster ID")
    emr_step_id: Optional[str] = Field(None, description="EMR step ID")
    failure_cause: Optional[str] = Field(None, description="Failure cause from execution")
    error_message: Optional[str] = Field(None, description="Error message")
    tier: Optional[Tier] = Field(None, description="Environment tier")


class APIFailureEvent(BaseEvent):
    """API/service failure event from ECS/CloudWatch."""
    
    event_type: EventType = Field(default=EventType.API_FAILURE, description="Event type")
    service_name: str = Field(..., description="ECS service name")
    cluster_name: Optional[str] = Field(None, description="ECS cluster name")
    alarm_name: Optional[str] = Field(None, description="CloudWatch alarm name")
    error_rate: Optional[float] = Field(None, description="Error rate (0.0 to 1.0)", ge=0.0, le=1.0)
    latency_p99: Optional[float] = Field(None, description="P99 latency in milliseconds", ge=0.0)
    error_code: Optional[str] = Field(None, description="HTTP error code (e.g., 503)")
    tier: Optional[Tier] = Field(None, description="Environment tier")


class DQCheckRequestEvent(BaseEvent):
    """Data quality check request event."""
    
    event_type: EventType = Field(default=EventType.DQ_CHECK_REQUEST, description="Event type")
    dataset_id: str = Field(..., description="Dataset identifier (e.g., 'raw.events')")
    partition: Optional[str] = Field(None, description="Partition to check (e.g., '2024-01-15')")
    partitions: Optional[list[str]] = Field(None, description="Multiple partitions to check")
    ruleset_id: Optional[str] = Field(None, description="DQ ruleset ID to use")
    triggered_by: Optional[str] = Field(None, description="What triggered this check (e.g., pipeline completion)")


class DQScheduledCheckEvent(BaseEvent):
    """Scheduled data quality check event."""
    
    event_type: EventType = Field(default=EventType.DQ_SCHEDULED_CHECK, description="Event type")
    dataset_ids: Optional[list[str]] = Field(None, description="Specific datasets to check (None = all critical)")
    check_all_critical: bool = Field(default=True, description="Check all critical datasets if dataset_ids not specified")


class DailySweepEvent(BaseEvent):
    """Daily sweep event for proactive health checks."""
    
    event_type: EventType = Field(default=EventType.DAILY_SWEEP, description="Event type")
    workflow_names: Optional[list[str]] = Field(None, description="Specific workflows to check (None = all)")
    check_dq: bool = Field(default=True, description="Run data quality checks")
    check_api_health: bool = Field(default=True, description="Check API health")
    check_cost: bool = Field(default=False, description="Run cost quick scan")


class CostDailyScanEvent(BaseEvent):
    """Daily cost optimization scan event."""
    
    event_type: EventType = Field(default=EventType.COST_DAILY_SCAN, description="Event type")
    time_range_days: int = Field(default=7, description="Number of days to analyze", ge=1, le=90)
    focus_services: Optional[list[str]] = Field(None, description="Specific services to focus on")


class CostWeeklyReviewEvent(BaseEvent):
    """Weekly deep cost review event."""
    
    event_type: EventType = Field(default=EventType.COST_WEEKLY_REVIEW, description="Event type")
    time_range_days: int = Field(default=30, description="Number of days to analyze", ge=7, le=90)
    generate_report: bool = Field(default=True, description="Generate detailed cost report")


class PipelineSLACheckEvent(BaseEvent):
    """Pipeline SLA check event (for late/missing data detection)."""
    
    event_type: EventType = Field(default=EventType.PIPELINE_SLA_CHECK, description="Event type")
    workflow_name: Optional[str] = Field(None, description="Specific workflow to check (None = all)")
    expected_execution_time: Optional[datetime] = Field(None, description="Expected execution time")
    check_window_hours: int = Field(default=24, description="Time window to check for missing/late executions", ge=1)


# Union type for all events
Event = (
    PipelineFailureEvent
    | APIFailureEvent
    | DQCheckRequestEvent
    | DQScheduledCheckEvent
    | DailySweepEvent
    | CostDailyScanEvent
    | CostWeeklyReviewEvent
    | PipelineSLACheckEvent
)
