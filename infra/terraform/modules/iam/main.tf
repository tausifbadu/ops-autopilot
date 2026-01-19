# IAM Module - Creates IAM roles and policies
# Placeholder - implement actual policies

variable "environment" {
  type = string
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "sqs_queue_urls" {
  type = map(string)
}

variable "dynamodb_tables" {
  type = map(string)
}

variable "s3_buckets" {
  type = map(string)
}

# ECS Execution Role (for pulling images, writing logs)
resource "aws_iam_role" "ecs_execution" {
  name = "${var.environment}-ops-autopilot-ecs-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# Agent Host Task Role
resource "aws_iam_role" "agent_host_task" {
  name = "${var.environment}-ops-autopilot-agent-host-task"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# MCP Server Task Roles (one per server)
resource "aws_iam_role" "mcp_server_tasks" {
  for_each = toset([
    "orchestration-sfn",
    "observability-cloudwatch",
    "data-execution-glue-emr",
    "runtime-ecs",
    "data-quality-athena",
    "finops",
    "devtools-github",
    "chatops",
  ])
  
  name = "${var.environment}-ops-autopilot-mcp-${each.key}-task"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

output "ecs_execution_role_arn" {
  value = aws_iam_role.ecs_execution.arn
}

output "agent_host_task_role_arn" {
  value = aws_iam_role.agent_host_task.arn
}

output "mcp_server_task_role_arns" {
  value = { for k, v in aws_iam_role.mcp_server_tasks : k => v.arn }
}
