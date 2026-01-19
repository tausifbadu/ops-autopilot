# EventBridge Module - Creates EventBridge rules
# Placeholder - implement event routing rules

variable "environment" {
  type = string
}

variable "sqs_queue_urls" {
  type = map(string)
}

# TODO: Implement EventBridge rules for:
# - Step Functions execution failures → incidents queue
# - CloudWatch alarms → incidents queue
# - Scheduled daily sweep → daily_sweep queue
# - Scheduled cost scan → cost_scan queue
