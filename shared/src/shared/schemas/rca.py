"""Root Cause Analysis (RCA) packet models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .common import Confidence, S3Reference, Severity


class FailureClassification(str, Enum):
    """Pipeline failure classification types."""
    
    DATA_LATE_MISSING = "DATA_LATE_MISSING"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    DEPENDENCY_OUTAGE = "DEPENDENCY_OUTAGE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    OOM_TIMEOUT = "OOM_TIMEOUT"
    PERMISSIONS = "PERMISSIONS"
    CODE_REGRESSION = "CODE_REGRESSION"
    UNKNOWN = "UNKNOWN"


class APIClassification(str, Enum):
    """API incident classification types."""
    
    DEPLOY_REGRESSION = "DEPLOY_REGRESSION"
    SATURATION = "SATURATION"
    CRASH_LOOP_OOM = "CRASH_LOOP_OOM"
    DEPENDENCY_OUTAGE = "DEPENDENCY_OUTAGE"
    MISCONFIG = "MISCONFIG"
    CODE_BUG = "CODE_BUG"
    UNKNOWN = "UNKNOWN"


class RecommendedAction(BaseModel):
    """A recommended remediation action."""
    
    action_type: str = Field(..., description="Action type (e.g., 'rerun_pipeline', 'restart_service')")
    description: str = Field(..., description="Human-readable description")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    estimated_impact: Optional[str] = Field(None, description="Estimated impact")
    risk_level: Optional[str] = Field(None, description="Risk level (low, medium, high)")


class ImpactAnalysis(BaseModel):
    """Impact analysis of an incident."""
    
    downstream_workflows: list[str] = Field(default_factory=list, description="Affected downstream workflows")
    data_impact: Optional[str] = Field(None, description="Data impact description")
    affected_partitions: list[str] = Field(default_factory=list, description="Affected data partitions")
    user_impact: Optional[str] = Field(None, description="User-facing impact")
    cost_impact: Optional[float] = Field(None, description="Estimated cost impact")


class PipelineIncidentAnalysis(BaseModel):
    """Pipeline failure RCA analysis result."""
    
    classification: FailureClassification = Field(..., description="Failure classification")
    confidence: Confidence = Field(..., description="Confidence score")
    root_cause_hypothesis: str = Field(..., description="Root cause hypothesis")
    evidence_refs: list[S3Reference] = Field(default_factory=list, description="References to evidence")
    recommended_actions: list[RecommendedAction] = Field(default_factory=list, description="Recommended actions")
    safe_to_autofix: bool = Field(default=False, description="Whether safe to auto-fix")
    impact: Optional[ImpactAnalysis] = Field(None, description="Impact analysis")
    timeline: Optional[list[dict[str, Any]]] = Field(None, description="Timeline of events")
    evidence_gaps: list[str] = Field(default_factory=list, description="Missing evidence needed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ApiIncidentAnalysis(BaseModel):
    """API/service incident RCA analysis result."""
    
    classification: APIClassification = Field(..., description="Incident classification")
    confidence: Confidence = Field(..., description="Confidence score")
    root_cause: str = Field(..., description="Root cause description")
    evidence_refs: list[S3Reference] = Field(default_factory=list, description="References to evidence")
    recommended_actions: list[RecommendedAction] = Field(default_factory=list, description="Recommended actions")
    actions_taken: list[dict[str, Any]] = Field(default_factory=list, description="Actions already taken")
    verification: Optional[dict[str, Any]] = Field(None, description="Verification results")
    error_rate: Optional[float] = Field(None, description="Current error rate")
    latency_p99: Optional[float] = Field(None, description="Current P99 latency")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataQualityResult(BaseModel):
    """Data quality check result."""
    
    dataset_id: str = Field(..., description="Dataset identifier")
    partitions: list[str] = Field(default_factory=list, description="Partitions checked")
    overall_status: str = Field(..., description="Overall status (PASS, FAIL, WARN)")
    checks: list[dict[str, Any]] = Field(default_factory=list, description="Individual check results")
    likely_cause: Optional[str] = Field(None, description="Likely cause if failed")
    impacted_downstream: list[str] = Field(default_factory=list, description="Impacted downstream workflows")
    severity: Optional[Severity] = Field(None, description="Severity if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RemediationPlan(BaseModel):
    """Remediation plan with actions to execute."""
    
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:16]}", description="Plan ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Plan creation time")
    actions: list[RecommendedAction] = Field(..., description="Actions to execute")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    rollback_plan: Optional[dict[str, Any]] = Field(None, description="Rollback plan if needed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RemediationResult(BaseModel):
    """Result of remediation execution."""
    
    plan_id: str = Field(..., description="Remediation plan ID")
    actions_taken: list[dict[str, Any]] = Field(default_factory=list, description="Actions executed with results")
    verification: dict[str, Any] = Field(default_factory=dict, description="Verification results")
    status: str = Field(..., description="Remediation status (success, failure, partial)")
    rollback_needed: bool = Field(default=False, description="Whether rollback is needed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BugFixProposal(BaseModel):
    """Code fix proposal from Code Fix Agent."""
    
    bug_location: dict[str, Any] = Field(..., description="Bug location (repository, file, line, function)")
    root_cause: str = Field(..., description="Root cause description")
    proposed_fix: dict[str, Any] = Field(..., description="Proposed fix (diff, explanation)")
    test_cases: list[str] = Field(default_factory=list, description="Suggested test cases")
    pr_created: bool = Field(default=False, description="Whether PR was created")
    pr_url: Optional[str] = Field(None, description="PR URL if created")
    confidence: Optional[Confidence] = Field(None, description="Confidence in the fix")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CostOptimizationReport(BaseModel):
    """Cost optimization report from Cost Agent."""
    
    time_range: str = Field(..., description="Time range analyzed")
    total_cost: float = Field(..., description="Total cost in time range")
    recommendations: list[dict[str, Any]] = Field(default_factory=list, description="Cost optimization recommendations")
    total_potential_savings: float = Field(..., description="Total potential monthly savings")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DailyDigest(BaseModel):
    """Daily sweep digest."""
    
    date: str = Field(..., description="Date of digest (YYYY-MM-DD)")
    workflows_checked: int = Field(..., description="Number of workflows checked", ge=0)
    issues_found: int = Field(..., description="Number of issues found", ge=0)
    incidents_created: list[dict[str, Any]] = Field(default_factory=list, description="Incidents created")
    cost_anomalies: list[dict[str, Any]] = Field(default_factory=list, description="Cost anomalies detected")
    summary: str = Field(..., description="Human-readable summary")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Digest generation time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DecisionPacket(BaseModel):
    """Coordinator agent decision packet (final output)."""
    
    incident_id: str = Field(..., description="Incident ID")
    what_happened: str = Field(..., description="What happened summary")
    evidence_collected: list[S3Reference] = Field(default_factory=list, description="Evidence collected")
    root_cause: dict[str, Any] = Field(..., description="Root cause analysis")
    auto_fixed: list[dict[str, Any]] = Field(default_factory=list, description="Actions auto-fixed")
    needs_human: list[dict[str, Any]] = Field(default_factory=list, description="Items needing human attention")
    tickets_created: list[dict[str, Any]] = Field(default_factory=list, description="Tickets created")
    prs_created: list[dict[str, Any]] = Field(default_factory=list, description="PRs created")
    notifications_sent: list[dict[str, Any]] = Field(default_factory=list, description="Notifications sent")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Packet creation time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
