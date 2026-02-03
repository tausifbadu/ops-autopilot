"""
Transform EventBridge events (Glue, EMR, or other) into PipelineFailureEvent JSON and send to SQS.
All EventBridge events routed to this Lambda are transformed and sent to SQS; unknown types use a generic payload.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3

SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
DEFAULT_TIER = os.environ.get("DEFAULT_TIER", "nonprod")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle EventBridge event: map to PipelineFailureEvent and send to SQS.
    Glue/EMR use specific mappers; all other events use a generic fallback so nothing is dropped.
    """
    if not SQS_QUEUE_URL:
        raise ValueError("SQS_QUEUE_URL environment variable is required")

    detail_type = event.get("detail-type")
    detail = event.get("detail") or {}
    source = event.get("source", "EventBridge")
    time_str = event.get("time") or datetime.now(timezone.utc).isoformat()

    if detail_type == "Glue Job State Change":
        payload = _glue_to_pipeline_failure(detail, source, time_str)
    elif detail_type == "EMR Serverless Job Run State Change":
        payload = _emr_serverless_to_pipeline_failure(detail, source, time_str)
    elif detail_type == "EMR Step State Change":
        payload = _emr_cluster_step_to_pipeline_failure(detail, source, time_str)
    else:
        payload = _generic_to_pipeline_failure(event, detail_type, source, time_str)

    sqs = boto3.client("sqs")
    send_params = {
        "QueueUrl": SQS_QUEUE_URL,
        "MessageBody": json.dumps(payload),
    }
    # FIFO queues require MessageGroupId and a dedup id. Use EventBridge event id so each
    # distinct failure creates a message; same event retried is deduplicated within 5 min.
    if SQS_QUEUE_URL.rstrip("/").endswith(".fifo"):
        send_params["MessageGroupId"] = "pipeline-failures"
        # Unique per event: EventBridge event id, or fallback to job/run/time so same job failing again = new message
        dedup_id = event.get("id")
        if not dedup_id:
            dedup_id = _make_dedup_id(payload)
        send_params["MessageDeduplicationId"] = dedup_id[:128]  # SQS limit 128 chars
    sqs.send_message(**send_params)
    return {"statusCode": 200, "body": json.dumps({"sent": True, "event_type": payload.get("event_type")})}


def _make_dedup_id(payload: dict[str, Any]) -> str:
    """Build a unique dedup id from payload when EventBridge event id is not available."""
    import hashlib
    # Prefer job/run identifiers so each run is a distinct message
    parts = [
        payload.get("glue_job_name") or payload.get("emr_cluster_id") or "pipeline",
        payload.get("glue_job_run_id") or payload.get("emr_step_id") or "",
        payload.get("timestamp", ""),
    ]
    body = json.dumps(payload, sort_keys=True)
    return hashlib.sha256((body + "|" + "|".join(parts)).encode()).hexdigest()


def _generic_to_pipeline_failure(
    event: dict[str, Any], detail_type: str, source: str, time_str: str
) -> dict:
    """Map any EventBridge event to a generic PipelineFailureEvent so all events go to SQS."""
    detail = event.get("detail") or {}
    state = detail.get("state", "UNKNOWN")
    message = detail.get("message") or detail.get("errorMessage") or f"Event: {detail_type} from {source}"
    return {
        "event_type": "PIPELINE_FAILURE",
        "source": source,
        "timestamp": time_str,
        "failure_cause": state if isinstance(state, str) else str(state),
        "error_message": message,
        "tier": DEFAULT_TIER,
        "detail_type": detail_type,
        "raw_detail": detail,
    }


def _glue_to_pipeline_failure(detail: dict, source: str, time_str: str) -> dict:
    """Map Glue Job State Change detail to PipelineFailureEvent schema."""
    state = detail.get("state", "FAILED")
    job_name = detail.get("jobName", "")
    job_run_id = detail.get("jobRunId", "")
    message = detail.get("message", f"Glue job state: {state}")

    return {
        "event_type": "PIPELINE_FAILURE",
        "source": source,
        "timestamp": time_str,
        "glue_job_name": job_name,
        "glue_job_run_id": job_run_id,
        "failure_cause": state,
        "error_message": message,
        "tier": DEFAULT_TIER,
    }


def _emr_cluster_step_to_pipeline_failure(detail: dict, source: str, time_str: str) -> dict:
    """Map EMR cluster (non-Serverless) Step State Change detail to PipelineFailureEvent schema."""
    cluster_id = detail.get("clusterId", "")
    step_id = detail.get("stepId", "")
    state = detail.get("state", "FAILED")
    message = detail.get("message", f"EMR cluster step state: {state}")

    return {
        "event_type": "PIPELINE_FAILURE",
        "source": source,
        "timestamp": time_str,
        "emr_cluster_id": cluster_id,
        "emr_step_id": step_id,
        "failure_cause": state,
        "error_message": message,
        "tier": DEFAULT_TIER,
    }


def _emr_serverless_to_pipeline_failure(detail: dict, source: str, time_str: str) -> dict:
    """Map EMR Serverless Job Run State Change detail to PipelineFailureEvent schema."""
    # EMR Serverless uses jobRunId, applicationId, etc.
    job_run_id = detail.get("jobRunId", "")
    application_id = detail.get("applicationId", "")
    state = detail.get("state", "FAILED")
    message = detail.get("message", f"EMR Serverless job run state: {state}")

    return {
        "event_type": "PIPELINE_FAILURE",
        "source": source,
        "timestamp": time_str,
        "emr_cluster_id": application_id,  # EMR Serverless uses applicationId
        "emr_step_id": job_run_id,
        "failure_cause": state,
        "error_message": message,
        "tier": DEFAULT_TIER,
    }
