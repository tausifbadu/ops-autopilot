# SQS Module - Creates SQS queues

variable "environment" {
  type = string
}

resource "aws_sqs_queue" "incidents" {
  name                       = "${var.environment}-ops-autopilot-incidents.fifo"
  fifo_queue                 = true
  content_based_deduplication = true
  
  visibility_timeout_seconds = 300  # 5 minutes
  message_retention_seconds  = 1209600  # 14 days
  
  tags = {
    Name        = "${var.environment}-incidents-queue"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "dq_checks" {
  name                       = "${var.environment}-ops-autopilot-dq-checks.fifo"
  fifo_queue                 = true
  content_based_deduplication = true
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600
  
  tags = {
    Name        = "${var.environment}-dq-checks-queue"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "cost_scan" {
  name                       = "${var.environment}-ops-autopilot-cost-scan"
  fifo_queue                 = false
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600
  
  tags = {
    Name        = "${var.environment}-cost-scan-queue"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "daily_sweep" {
  name                       = "${var.environment}-ops-autopilot-daily-sweep"
  fifo_queue                 = false
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600
  
  tags = {
    Name        = "${var.environment}-daily-sweep-queue"
    Environment = var.environment
  }
}

output "queue_urls" {
  value = {
    incidents  = aws_sqs_queue.incidents.url
    dq_checks  = aws_sqs_queue.dq_checks.url
    cost_scan  = aws_sqs_queue.cost_scan.url
    daily_sweep = aws_sqs_queue.daily_sweep.url
  }
}
