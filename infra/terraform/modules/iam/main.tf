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
  type    = map(string)
  default = {}
}

variable "sqs_queue_arns" {
  description = "SQS queue ARNs for IAM policy (use queue ARN, not URL, for Resource)"
  type        = map(string)
  default     = {}
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

variable "ecs_secret_arns" {
  description = "ARNs of secrets (e.g. LLM API key) that ECS tasks need at startup; execution role gets GetSecretValue"
  type        = list(string)
  default     = []
}

# ECS Execution Role (for pulling images, writing logs, reading secrets)
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

# ECS Execution Role Policy: ECR pull + CloudWatch Logs
resource "aws_iam_role_policy" "ecs_execution" {
  name = "${var.environment}-ops-autopilot-ecs-execution-policy"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = ["ecr:GetAuthorizationToken"]
          Resource = "*"
        },
        {
          Effect = "Allow"
          Action = [
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage"
          ]
          Resource = "arn:aws:ecr:${var.region}:${var.account_id}:repository/*"
        },
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/ecs/${var.environment}/*:*"
        }
      ],
      length(var.ecs_secret_arns) > 0 ? [{
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.ecs_secret_arns
      }] : []
    )
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
    "data-execution-glue-emr",
    "observability-cloudwatch",
    "devtools-github",
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

############################################
# Glue Studio Notebook Role (full access)
############################################
resource "aws_iam_role" "glue_notebook" {
  name = "${var.environment}-ops-autopilot-glue-notebook"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_notebook_service_role" {
  role       = aws_iam_role.glue_notebook.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_notebook_s3_full" {
  role       = aws_iam_role.glue_notebook.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "glue_notebook_logs_full" {
  role       = aws_iam_role.glue_notebook.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_iam_role_policy" "glue_notebook_passrole" {
  name = "${var.environment}-ops-autopilot-glue-notebook-passrole"
  role = aws_iam_role.glue_notebook.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.glue_notebook.arn,
          "arn:aws:iam::${var.account_id}:role/${var.environment}-ops-autopilot-glue-test-job"
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "glue.amazonaws.com"
          }
        }
      }
    ]
  })
}

output "glue_notebook_role_arn" {
  value = aws_iam_role.glue_notebook.arn
}

# Agent Host Task Role Policy
resource "aws_iam_role_policy" "agent_host_task" {
  name = "${var.environment}-ops-autopilot-agent-host-task-policy"
  role = aws_iam_role.agent_host_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # SQS permissions (queue ARNs required for IAM Resource)
      length(var.sqs_queue_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ]
          Resource = [for arn in values(var.sqs_queue_arns) : arn]
        }
      ] : [],
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

# MCP Server Task Role Policies - data-execution-glue-emr needs Glue read for get_glue_job_run / list_glue_job_runs
resource "aws_iam_role_policy" "mcp_data_execution_glue" {
  for_each = toset(["data-execution-glue-emr"])

  name   = "${var.environment}-ops-autopilot-mcp-${each.key}-glue-policy"
  role   = aws_iam_role.mcp_server_tasks[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:GetJob",
          "glue:GetJobRun",
          "glue:GetJobRuns"
        ]
        Resource = "arn:aws:glue:${var.region}:${var.account_id}:job/*"
      }
    ]
  })
}

output "mcp_server_task_role_arns" {
  value = { for k, v in aws_iam_role.mcp_server_tasks : k => v.arn }
}
