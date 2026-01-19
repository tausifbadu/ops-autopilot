terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Uncomment and configure for remote state
  # backend "s3" {
  #   bucket = "ops-autopilot-terraform-state"
  #   key    = "terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "ops-autopilot"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# ECR Repositories for Docker images
module "ecr" {
  source = "./modules/ecr"
  
  repositories = [
    "ops-autopilot/agent-host",
    "ops-autopilot/mcp-orchestration-sfn",
    "ops-autopilot/mcp-observability-cloudwatch",
    "ops-autopilot/mcp-data-execution-glue-emr",
    "ops-autopilot/mcp-runtime-ecs",
    "ops-autopilot/mcp-data-quality-athena",
    "ops-autopilot/mcp-finops",
    "ops-autopilot/mcp-devtools-github",
    "ops-autopilot/mcp-chatops",
  ]
  
  environment = var.environment
}

# SQS Queues
module "sqs" {
  source = "./modules/sqs"
  
  environment = var.environment
}

# DynamoDB Tables
module "dynamodb" {
  source = "./modules/dynamodb"
  
  environment = var.environment
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  environment = var.environment
}

# IAM Roles
module "iam" {
  source = "./modules/iam"
  
  environment     = var.environment
  account_id      = data.aws_caller_identity.current.account_id
  region          = data.aws_region.current.name
  sqs_queue_urls  = module.sqs.queue_urls
  dynamodb_tables = module.dynamodb.table_names
  s3_buckets      = module.s3.bucket_names
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-ops-autopilot-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "${var.environment}-ops-autopilot-cluster"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "agent_host" {
  name              = "/ecs/${var.environment}/ops-autopilot/agent-host"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name = "${var.environment}-agent-host-logs"
  }
}

resource "aws_cloudwatch_log_group" "mcp_servers" {
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
  
  name              = "/ecs/${var.environment}/ops-autopilot/mcp-${each.key}"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name = "${var.environment}-mcp-${each.key}-logs"
  }
}

# ECS Task Definitions and Services
module "agent_host" {
  source = "./modules/ecs-service"
  
  name                = "agent-host"
  environment         = var.environment
  cluster_id          = aws_ecs_cluster.main.id
  ecr_repository_uri  = module.ecr.repository_uris["ops-autopilot/agent-host"]
  task_role_arn       = module.iam.agent_host_task_role_arn
  execution_role_arn  = module.iam.ecs_execution_role_arn
  log_group_name     = aws_cloudwatch_log_group.agent_host.name
  
  cpu    = var.agent_host_cpu
  memory = var.agent_host_memory
  
  desired_count = var.agent_host_desired_count
  
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.ecs_security_group_id]
  
  environment_variables = {
    AWS_REGION            = var.aws_region
    ENVIRONMENT           = var.environment
    MCP_ORCHESTRATION_URL = "http://${module.mcp_servers["orchestration-sfn"].service_name}.${var.environment}.local:8001"
    MCP_OBSERVABILITY_URL = "http://${module.mcp_servers["observability-cloudwatch"].service_name}.${var.environment}.local:8002"
    SQS_QUEUE_INCIDENTS   = module.sqs.queue_urls["incidents"]
    SQS_QUEUE_DQ          = module.sqs.queue_urls["dq_checks"]
    SQS_QUEUE_COST        = module.sqs.queue_urls["cost_scan"]
    SQS_QUEUE_DAILY       = module.sqs.queue_urls["daily_sweep"]
    DYNAMODB_REGISTRY     = module.dynamodb.table_names["workflow_registry"]
    DYNAMODB_INCIDENTS    = module.dynamodb.table_names["incidents"]
    S3_EVIDENCE_BUCKET    = module.s3.bucket_names["evidence"]
    LLM_PROVIDER          = var.llm_provider
  }
  
  secrets = {
    # Add secrets from AWS Secrets Manager or Parameter Store
    # LLM_API_KEY = "arn:aws:secretsmanager:..."
  }
}

# MCP Servers
module "mcp_servers" {
  source = "./modules/ecs-service"
  
  for_each = {
    "orchestration-sfn" = {
      port = 8001
      cpu  = 256
      memory = 512
    }
    "observability-cloudwatch" = {
      port = 8002
      cpu  = 256
      memory = 512
    }
    "data-execution-glue-emr" = {
      port = 8003
      cpu  = 256
      memory = 512
    }
    "runtime-ecs" = {
      port = 8004
      cpu  = 256
      memory = 512
    }
    "data-quality-athena" = {
      port = 8005
      cpu  = 256
      memory = 512
    }
    "finops" = {
      port = 8006
      cpu  = 256
      memory = 512
    }
    "devtools-github" = {
      port = 8007
      cpu  = 256
      memory = 512
    }
    "chatops" = {
      port = 8008
      cpu  = 256
      memory = 512
    }
  }
  
  name                = "mcp-${each.key}"
  environment         = var.environment
  cluster_id          = aws_ecs_cluster.main.id
  ecr_repository_uri   = module.ecr.repository_uris["ops-autopilot/mcp-${each.key}"]
  task_role_arn       = module.iam.mcp_server_task_role_arns[each.key]
  execution_role_arn  = module.iam.ecs_execution_role_arn
  log_group_name      = aws_cloudwatch_log_group.mcp_servers[each.key].name
  
  cpu    = each.value.cpu
  memory = each.value.memory
  
  desired_count = var.mcp_server_desired_count
  
  container_port = each.value.port
  
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids  = [module.vpc.ecs_security_group_id]
  
  environment_variables = {
    HOST              = "0.0.0.0"
    PORT              = tostring(each.value.port)
    AWS_REGION        = var.aws_region
    ENVIRONMENT       = var.environment
    ALLOWLIST_ENABLED = "true"
    LOG_LEVEL         = "INFO"
  }
}

# Application Load Balancer (optional, for MCP servers if needed)
module "alb" {
  source = "./modules/alb"
  
  environment      = var.environment
  vpc_id           = module.vpc.vpc_id
  subnet_ids       = module.vpc.public_subnet_ids
  security_groups  = [module.vpc.alb_security_group_id]
  
  mcp_services = module.mcp_servers
}

# EventBridge Rules
module "eventbridge" {
  source = "./modules/eventbridge"
  
  environment     = var.environment
  sqs_queue_urls  = module.sqs.queue_urls
}
