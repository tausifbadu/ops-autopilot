# EventBridge Module - All Glue/EMR/other failure events → Lambda (transform) → SQS
# Going forward, all EventBridge events (Glue, EMR, or other) MUST go through the Lambda transformer.
# Add new rules here with the same Lambda target for any additional event sources.

variable "environment" {
  type = string
}

variable "region" {
  type        = string
  default     = ""
  description = "AWS region (optional, for naming)."
}

variable "lambda_function_arn" {
  type        = string
  description = "ARN of Lambda that transforms events and sends to SQS (required)."
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda (for EventBridge invoke permission, required)."
}

# ---------------------------------------------------------------------------
# Glue Job Failure → Lambda → SQS
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "glue_job_failure" {
  name        = "${var.environment}-ops-autopilot-glue-job-failure"
  description = "Glue job FAILED/TIMEOUT → Lambda → SQS"

  event_pattern = jsonencode({
    source      = ["aws.glue"]
    detail-type = ["Glue Job State Change"]
    detail = {
      state = ["FAILED", "TIMEOUT"]
    }
  })

  tags = {
    Name = "${var.environment}-glue-job-failure-rule"
  }
}

resource "aws_cloudwatch_event_target" "glue_failure_to_lambda" {
  rule      = aws_cloudwatch_event_rule.glue_job_failure.name
  target_id = "PipelineEventTransformer"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "eventbridge_glue" {
  statement_id  = "AllowExecutionFromEventBridgeGlue"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.glue_job_failure.arn
}

# ---------------------------------------------------------------------------
# EMR Cluster (non-Serverless) Step Failure → Lambda → SQS
# Classic EMR clusters emit "EMR Step State Change" events when a step fails or is cancelled.
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "emr_cluster_step_failure" {
  name        = "${var.environment}-ops-autopilot-emr-cluster-step-failure"
  description = "EMR cluster step FAILED/CANCELLED → Lambda → SQS"

  event_pattern = jsonencode({
    source      = ["aws.emr"]
    detail-type = ["EMR Step State Change"]
    detail = {
      state = ["FAILED", "CANCELLED"]
    }
  })

  tags = {
    Name = "${var.environment}-emr-cluster-step-failure-rule"
  }
}

resource "aws_cloudwatch_event_target" "emr_cluster_step_failure_to_lambda" {
  rule      = aws_cloudwatch_event_rule.emr_cluster_step_failure.name
  target_id = "PipelineEventTransformer"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "eventbridge_emr_cluster_step" {
  statement_id  = "AllowExecutionFromEventBridgeEMRClusterStep"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.emr_cluster_step_failure.arn
}

# ---------------------------------------------------------------------------
# EMR Serverless Job Run Failure → Lambda → SQS
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "emr_serverless_job_failure" {
  name        = "${var.environment}-ops-autopilot-emr-serverless-job-failure"
  description = "EMR Serverless job FAILED/CANCELLED → Lambda → SQS"

  event_pattern = jsonencode({
    source      = ["aws.emr-serverless"]
    detail-type = ["EMR Serverless Job Run State Change"]
    detail = {
      state = ["FAILED", "CANCELLED"]
    }
  })

  tags = {
    Name = "${var.environment}-emr-serverless-job-failure-rule"
  }
}

resource "aws_cloudwatch_event_target" "emr_serverless_failure_to_lambda" {
  rule      = aws_cloudwatch_event_rule.emr_serverless_job_failure.name
  target_id = "PipelineEventTransformer"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "eventbridge_emr_serverless" {
  statement_id  = "AllowExecutionFromEventBridgeEMRServerless"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.emr_serverless_job_failure.arn
}

# ---------------------------------------------------------------------------
# To add more event sources (e.g. Glue Crawler, Step Functions, custom):
# 1. Add aws_cloudwatch_event_rule with the event pattern
# 2. Add aws_cloudwatch_event_target with arn = var.lambda_function_arn
# 3. Add aws_lambda_permission with source_arn = the new rule's arn
# 4. Extend the Lambda handler to map that detail-type to PipelineFailureEvent (or use generic fallback)
# ---------------------------------------------------------------------------
