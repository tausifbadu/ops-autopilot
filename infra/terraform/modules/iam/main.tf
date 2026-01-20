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

variable "enable_global_resources" {
  type    = bool
  default = false
}

variable "dynamodb_primary_region" {
  type    = string
  default = ""
}

variable "s3_evidence_region" {
  type    = string
  default = ""
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

# Agent Host Task Role Policy
resource "aws_iam_role_policy" "agent_host_task" {
  name = "${var.environment}-ops-autopilot-agent-host-task-policy"
  role = aws_iam_role.agent_host_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # Regional SQS permissions
      [
        {
          Effect = "Allow"
          Action = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ]
          Resource = [for url in values(var.sqs_queue_urls) : url]
        }
      ],
      # DynamoDB permissions (global or regional)
      var.enable_global_resources ? [
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan"
          ]
          Resource = [
            for table in values(var.dynamodb_tables) : "arn:aws:dynamodb:*:*:table/${table}"
          ]
        }
      ] : [
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan"
          ]
          Resource = [
            for table in values(var.dynamodb_tables) : "arn:aws:dynamodb:${var.region}:${var.account_id}:table/${table}"
          ]
        }
      ],
      # S3 permissions (global or regional)
      var.enable_global_resources ? [
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ]
          Resource = [
            for bucket in values(var.s3_buckets) : "arn:aws:s3:::${bucket}/*"
          ]
        },
        {
          Effect = "Allow"
          Action = [
            "s3:ListBucket"
          ]
          Resource = [
            for bucket in values(var.s3_buckets) : "arn:aws:s3:::${bucket}"
          ]
        }
      ] : [
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ]
          Resource = [
            for bucket in values(var.s3_buckets) : "arn:aws:s3:::${bucket}/*"
          ]
        },
        {
          Effect = "Allow"
          Action = [
            "s3:ListBucket"
          ]
          Resource = [
            for bucket in values(var.s3_buckets) : "arn:aws:s3:::${bucket}"
          ]
        }
      ],
      # CloudWatch Logs
      [
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "arn:aws:logs:${var.region}:${var.account_id}:*"
        }
      ]
    )
  })
}

# MCP Server Task Role Policies (placeholder - add specific permissions per server)
# For now, they inherit basic ECS permissions

output "ecs_execution_role_arn" {
  value = aws_iam_role.ecs_execution.arn
}

output "agent_host_task_role_arn" {
  value = aws_iam_role.agent_host_task.arn
}

output "mcp_server_task_role_arns" {
  value = { for k, v in aws_iam_role.mcp_server_tasks : k => v.arn }
}
