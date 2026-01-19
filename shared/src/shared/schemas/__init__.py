"""Shared schemas for ops-autopilot."""

# Common types
from .common import (
    BaseEvent,
    Confidence,
    ExecutionARN,
    IncidentID,
    S3Reference,
    Severity,
    StateMachineARN,
    Status,
    Tier,
    Timestamp,
    WorkflowMetadata,
)

# Event types
from .events import (
    APIFailureEvent,
    CostDailyScanEvent,
    CostWeeklyReviewEvent,
    DailySweepEvent,
    DQCheckRequestEvent,
    DQScheduledCheckEvent,
    Event,
    EventType,
    PipelineFailureEvent,
    PipelineSLACheckEvent,
)

# Evidence types
from .evidence import (
    DataQualityCheckResult,
    ECSServiceDetails,
    ECSTaskDetails,
    EMRStepDetails,
    EvidencePack,
    ExecutionDetails,
    ExecutionHistory,
    GlueJobRunDetails,
    LogEntry,
    LogEvidence,
    MetricDataPoint,
    MetricEvidence,
)

# RCA types
from .rca import (
    APIClassification,
    ApiIncidentAnalysis,
    BugFixProposal,
    CostOptimizationReport,
    DailyDigest,
    DataQualityResult,
    DecisionPacket,
    FailureClassification,
    ImpactAnalysis,
    PipelineIncidentAnalysis,
    RecommendedAction,
    RemediationPlan,
    RemediationResult,
)

__all__ = [
    # Common
    "BaseEvent",
    "Confidence",
    "ExecutionARN",
    "IncidentID",
    "S3Reference",
    "Severity",
    "StateMachineARN",
    "Status",
    "Tier",
    "Timestamp",
    "WorkflowMetadata",
    # Events
    "APIFailureEvent",
    "CostDailyScanEvent",
    "CostWeeklyReviewEvent",
    "DailySweepEvent",
    "DQCheckRequestEvent",
    "DQScheduledCheckEvent",
    "Event",
    "EventType",
    "PipelineFailureEvent",
    "PipelineSLACheckEvent",
    # Evidence
    "DataQualityCheckResult",
    "ECSServiceDetails",
    "ECSTaskDetails",
    "EMRStepDetails",
    "EvidencePack",
    "ExecutionDetails",
    "ExecutionHistory",
    "GlueJobRunDetails",
    "LogEntry",
    "LogEvidence",
    "MetricDataPoint",
    "MetricEvidence",
    # RCA
    "APIClassification",
    "ApiIncidentAnalysis",
    "BugFixProposal",
    "CostOptimizationReport",
    "DailyDigest",
    "DataQualityResult",
    "DecisionPacket",
    "FailureClassification",
    "ImpactAnalysis",
    "PipelineIncidentAnalysis",
    "RecommendedAction",
    "RemediationPlan",
    "RemediationResult",
]
