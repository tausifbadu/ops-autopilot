# Pipeline Event Transformer Lambda

**All** EventBridge events (Glue, EMR, or other) are routed to this Lambda. It transforms them into **PipelineFailureEvent** JSON and sends them to the incidents SQS queue. Nothing is dropped: unknown event types use a generic payload.

## Flow

1. **Event source** (Glue job failure, EMR Serverless job failure, or future rules) emits an event to EventBridge.
2. **EventBridge rules** match and invoke this Lambda (one rule per event type; all target this Lambda).
3. **Lambda** maps the event to `PipelineFailureEvent` (or a generic shape for unknown types) and sends to the incidents SQS queue.

## Environment variables

- `SQS_QUEUE_URL` – incidents queue URL (required).
- `DEFAULT_TIER` – default tier for events (default: `nonprod`).

## Event handling

- **Glue Job State Change** – full mapping: `glue_job_name`, `glue_job_run_id`, `failure_cause`, `error_message`, etc.
- **EMR Step State Change** (classic EMR cluster, non-Serverless) – full mapping: `emr_cluster_id` (clusterId), `emr_step_id` (stepId), `failure_cause`, `error_message`, etc.
- **EMR Serverless Job Run State Change** – full mapping: `emr_cluster_id` (applicationId), `emr_step_id` (jobRunId), `failure_cause`, `error_message`, etc.
- **Other / unknown** – generic `PIPELINE_FAILURE` with `failure_cause`, `error_message`, `detail_type`, `raw_detail` so every event still reaches SQS.

## Adding new event sources

1. In Terraform (EventBridge module): add a new `aws_cloudwatch_event_rule`, `aws_cloudwatch_event_target` (Lambda), and `aws_lambda_permission`.
2. In this Lambda: add a branch for the new `detail-type` and a mapper, or rely on the generic fallback.

## Local testing

Use a Glue or EMR Serverless event payload (e.g. from EventBridge console) as the Lambda test event. Ensure `SQS_QUEUE_URL` is set in the Lambda configuration.
