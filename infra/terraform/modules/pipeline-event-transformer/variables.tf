variable "environment" {
  type = string
}

variable "lambda_source_path" {
  type        = string
  description = "Path to the Lambda source directory (containing handler.py)."
}

variable "sqs_queue_url" {
  type        = string
  description = "SQS queue URL (incidents) to send transformed events to."
}

variable "sqs_queue_arn" {
  type        = string
  description = "ARN of the incidents SQS queue (for Lambda IAM)."
}

variable "default_tier" {
  type        = string
  default     = "nonprod"
  description = "Default tier for PipelineFailureEvent (nonprod, prod, dev)."
}
