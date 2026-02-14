terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Remote state in S3. When you run plan/apply locally, Terraform uses your AWS credentials
  # to read state from S3 before the run and write the updated state back to S3 after apply.
  # Create the bucket once (e.g. aws s3 mb s3://ops-autopilot-terraform-state --region us-east-1).
  # Optional: add dynamodb_table for state locking (create table with LockID as partition key).
  backend "s3" {
    bucket = "ops-autopilot-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
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

# EMR service-linked role required for EMR cleanup
resource "aws_iam_service_linked_role" "emr_cleanup" {
  aws_service_name = "elasticmapreduce.amazonaws.com"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Optional: Terraform-managed OpenAI API key secret (when openai_api_key is set)
resource "aws_secretsmanager_secret" "openai_api_key" {
  count = var.openai_api_key != null && var.openai_api_key != "" ? 1 : 0

  name                    = "${var.environment}/ops-autopilot/openai-api-key"
  description             = "OpenAI API key for ops-autopilot Agent Host (LLM)"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  count = var.openai_api_key != null && var.openai_api_key != "" ? 1 : 0

  secret_id     = aws_secretsmanager_secret.openai_api_key[0].id
  secret_string = var.openai_api_key
}

locals {
  # Use Terraform-created secret ARN when openai_api_key is set, else use existing llm_api_key_secret_arn
  llm_api_key_secret_arn = (var.openai_api_key != null && var.openai_api_key != "") ? aws_secretsmanager_secret.openai_api_key[0].arn : (var.llm_api_key_secret_arn != null && var.llm_api_key_secret_arn != "" ? var.llm_api_key_secret_arn : "")
}

# VPC and Networking (required for ECS)
module "vpc" {
  source = "./modules/vpc"

  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"

  environment = var.environment
}

module "upload_csv" {
  source = "./modules/s3_upload"

  bucket_name = "ops-autopilot-data"
  s3_key      = "raw/csv/sample.csv"
  local_file  = "${path.module}/data/sample.csv"
}

module "upload_attendance_csv" {
  source = "./modules/s3_upload"

  bucket_name = "ops-autopilot-data"
  s3_key      = "raw/csv/attendance.csv"
  local_file  = "${path.module}/data/attendance.csv"
}

module "upload_all_csv" {
  source = "./modules/s3_upload"

  for_each = toset(fileset("${path.module}/data", "*.csv"))

  bucket_name = "ops-autopilot-data"
  s3_key      = "raw/csv/${each.value}"
  local_file  = "${path.module}/data/${each.value}"
}

# DynamoDB Tables
module "dynamodb" {
  source = "./modules/dynamodb"

  environment = var.environment
}


module "sqs" {
   source = "./modules/sqs"

   environment = var.environment
}

# ECR Repositories: agent-host + 4 MCP servers only
module "ecr" {
  source = "./modules/ecr"

  repositories = [
    "ops-autopilot/agent-host",
    "ops-autopilot/mcp-orchestration-sfn",
    "ops-autopilot/mcp-data-execution-glue-emr",
    "ops-autopilot/mcp-observability-cloudwatch",
    "ops-autopilot/mcp-devtools-github",
  ]

  environment = var.environment
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  environment     = var.environment
  account_id      = data.aws_caller_identity.current.account_id
  region          = data.aws_region.current.name
  sqs_queue_arns  = module.sqs.queue_arns
  dynamodb_tables = module.dynamodb.table_names
  s3_buckets      = module.s3.bucket_names
  ecs_secret_arns = local.llm_api_key_secret_arn != "" ? [local.llm_api_key_secret_arn] : []
}

# ---------------------------------------------------------------------------
# Pipeline failure: Glue -> EventBridge -> Lambda -> SQS + test Glue job
# Lambda transforms Glue/EMR failure events to PipelineFailureEvent JSON and sends to SQS.
# Glue test job fails on purpose so you can verify the pipeline in AWS.
# ---------------------------------------------------------------------------

# Glue test job (no SQS required): run in AWS Glue to trigger a failure event
module "glue_test_job" {
  source = "./modules/glue-test-job"

  environment        = var.environment
  script_bucket_name = module.s3.bucket_names["scripts"]
  script_key         = "glue-scripts/ops-autopilot-fail-for-test.py"
  script_source_path = "${path.root}/glue-scripts/ops-autopilot-fail-for-test.py"
}

module "glue_csv_parquet" {
  source = "./modules/glue-csv-parquet"

  environment        = var.environment
  script_bucket_name = module.s3.bucket_names["scripts"]
  script_key         = "glue-scripts/ops-autopilot-csv-to-parquet.py"
  script_source_path = "${path.root}/glue-scripts/ops-autopilot-csv-to-parquet.py"

  data_bucket_name = module.s3.bucket_names["data"]
  input_prefix     = "raw/csv/"
  output_prefix    = "stage/parquet/"
  temp_prefix      = "tmp/glue/"
}

module "emr_stepfn" {
  source = "./modules/emr_stepfn"

  environment        = var.environment
  script_bucket_name = module.s3.bucket_names["scripts"]
  script_key         = "glue-scripts/csv_to_parquet.py"
  script_source_path = "${path.root}/emr-job-scripts/print-hello.py"

  data_bucket_name = module.s3.bucket_names["data"]
  input_prefix     = "raw/csv/"
  output_prefix    = "stage/parquet/"
  log_prefix       = "emr-logs/"

  subnet_id = module.vpc.public_subnet_ids[0]
}

module "data_catalog" {
  source = "./modules/data_catalog"

  data_bucket_name        = module.s3.bucket_names["data"]
  database_name           = "electric-raw-dev"
  curated_database_name   = "electric-curated-dev"
}

# Glue job: generate raw electric tables (cheapest Glue job)
module "glue_generate_electric_raw" {
  source = "./modules/glue-generate-electric-raw"

  environment        = var.environment
  script_bucket_name = module.s3.bucket_names["scripts"]
  script_key         = "glue-scripts/generate_electric_raw_glue.py"
  script_source_path = "${path.root}/glue-scripts/generate_electric_raw_glue.py"

  data_bucket_name = module.s3.bucket_names["data"]
  output_prefix    = "raw/electric-raw-dev"
  max_rows         = 10000
  tables           = "all"
}

# module "emr_studio_cluster" {
#   source = "./modules/emr_studio_cluster"
#
#   environment          = var.environment
#   vpc_id               = module.vpc.vpc_id
#   subnet_id            = module.vpc.public_subnet_ids[0]
#   studio_subnet_ids    = module.vpc.public_subnet_ids
#   data_bucket_name     = module.s3.bucket_names["data"]
#   log_prefix           = "emr-studio-logs/"
#   master_instance_type = "m5.xlarge"
#
#   # Session mappings via Terraform (optional). Each identity gets Studio access + session policy (Runtime Role dropdown).
#   # Option A: single IAM user ID - studio_session_identity_id = "AIDAXXXXXXXX"
#   # Option B: multiple users/groups - studio_session_mappings = [
#   #   { identity_type = "USER", identity_id = "AIDAXXXXXXXX" },
#   #   { identity_type = "GROUP", identity_name = "emr-studio-users" },
#   # ]
#
#   # If attach fails with "notebook security group sg-xxx does not have ingress", add that SG ID here:
#   notebook_security_group_ids = ["sg-0269917657894b560"]
# }

# # Synthetic electric-raw-dev data generator (disabled; use Glue job instead)
# # ---------------------------------------------------------------------------
#
# resource "null_resource" "reset_electric_raw" {
#   triggers = {
#     reset_version = "v2"
#   }
#
#   provisioner "local-exec" {
#     command = "powershell -Command \"$ErrorActionPreference='Continue'; aws s3 rm s3://ops-autopilot-data/raw/electric-raw-dev/ --recursive; foreach ($t in @('customer','customer_agreement_table','meter','meter_geo_location','meter_usage','transformer_table','transformer_meter_mapping','transformer_geo_location','customer_meter_mapping')) { aws glue delete-table --database-name electric-raw-dev --name $t 2>$null; if ($LASTEXITCODE -ne 0) { $LASTEXITCODE = 0 } }; exit 0\""
#     working_dir = path.module
#   }
# }
#
# resource "null_resource" "generate_electric_raw" {
#   triggers = {
#     data_version = "v2"
#     tables       = "all"
#   }
#
#   provisioner "local-exec" {
#     command     = "python scripts/generate_electric_raw.py --out generated/electric-raw-dev --max-rows 10000 --max-mb 100 --tables ${self.triggers.tables}"
#     working_dir = path.module
#   }
#
#   depends_on = [null_resource.reset_electric_raw]
# }
#
# locals {
#   electric_raw_files = fileset("${path.module}/generated/electric-raw-dev", "**/*.parquet")
# }
#
# resource "aws_s3_object" "electric_raw" {
#   for_each = toset(local.electric_raw_files)
#
#   bucket = "ops-autopilot-data"
#   key    = "raw/electric-raw-dev/${each.value}"
#   source = "${path.module}/generated/electric-raw-dev/${each.value}"
#
#   depends_on = [null_resource.generate_electric_raw]
# }

module "pipeline_event_transformer" {
   source = "./modules/pipeline-event-transformer"

   environment        = var.environment
   lambda_source_path  = "${path.root}/lambda/pipeline-event-transformer"
   sqs_queue_url       = module.sqs.queue_urls["incidents"]
   sqs_queue_arn      = module.sqs.queue_arns["incidents"]
   default_tier        = var.environment == "prod" ? "prod" : "nonprod"
}

 module "eventbridge" {
   source = "./modules/eventbridge"

   environment          = var.environment
   lambda_function_arn  = module.pipeline_event_transformer.function_arn
   lambda_function_name = module.pipeline_event_transformer.function_name
}

 #---------------------------------------------------------------------------
 #ECS Cluster and Services - COMMENTED OUT (uncomment to recreate)
 #Run: terraform apply to destroy ECS + log groups; S3, DynamoDB, SQS, ECR, VPC, IAM remain
 #---------------------------------------------------------------------------
 # # ECS Cluster
 # resource "aws_ecs_cluster" "main" {
 #   name = "${var.environment}-ops-autopilot-cluster"
 #
 #   setting {
 #     name  = "containerInsights"
 #     value = "enabled"
 #   }
 #
 #   tags = {
 #     Name = "${var.environment}-ops-autopilot-cluster"
 #   }
 # }
 #
 # # CloudWatch Log Groups
 # resource "aws_cloudwatch_log_group" "agent_host" {
 #   name              = "/ecs/${var.environment}/ops-autopilot/agent-host"
 #   retention_in_days = var.log_retention_days
 #
 #   tags = {
 #     Name = "${var.environment}-agent-host-logs"
 #   }
 # }
 #
 # resource "aws_cloudwatch_log_group" "mcp_servers" {
 #   for_each = toset([
 #     "orchestration-sfn",
 #     "data-execution-glue-emr",
 #     "observability-cloudwatch",
 #     "devtools-github",
 #   ])
 #
 #   name              = "/ecs/${var.environment}/ops-autopilot/mcp-${each.key}"
 #   retention_in_days = var.log_retention_days
 #
 #   tags = {
 #     Name = "${var.environment}-mcp-${each.key}-logs"
 #   }
 # }
 #
 # # Service discovery so agent-host can resolve MCP hostnames (e.g. dev-mcp-data-execution-glue-emr.dev.local)
 # resource "aws_service_discovery_private_dns_namespace" "main" {
 #   name        = "${var.environment}.local"
 #   description = "Private DNS namespace for ECS service discovery (MCP servers)"
 #   vpc         = module.vpc.vpc_id
 # }
 #
 # resource "aws_service_discovery_service" "mcp" {
 #   for_each = toset([
 #     "orchestration-sfn",
 #     "data-execution-glue-emr",
 #     "observability-cloudwatch",
 #     "devtools-github",
 #   ])
 #
 #   name = "${var.environment}-mcp-${each.key}"
 #
 #   dns_config {
 #     namespace_id   = aws_service_discovery_private_dns_namespace.main.id
 #     dns_records {
 #       ttl  = 10
 #       type = "A"
 #     }
 #     routing_policy = "MULTIVALUE"
 #   }
 #
 #   health_check_custom_config {
 #     failure_threshold = 1
 #   }
 # }
 #
 # # ECS: Agent Host
 # module "agent_host" {
 #   source = "./modules/ecs-service"
 #
 #   name               = "agent-host"
 #   environment        = var.environment
 #   cluster_id         = aws_ecs_cluster.main.id
 #   ecr_repository_uri = module.ecr.repository_uris["ops-autopilot/agent-host"]
 #   task_role_arn      = module.iam.agent_host_task_role_arn
 #   execution_role_arn = module.iam.ecs_execution_role_arn
 #   log_group_name     = aws_cloudwatch_log_group.agent_host.name
 #
 #   cpu    = var.agent_host_cpu
 #   memory = var.agent_host_memory
 #
 #   desired_count = var.agent_host_desired_count
 #
 #   subnet_ids         = module.vpc.private_subnet_ids
 #   security_group_ids = [module.vpc.ecs_security_group_id]
 #
 #   environment_variables = merge(
 #     {
 #       AWS_REGION             = var.aws_region
 #       ENVIRONMENT            = var.environment
 #       SQS_QUEUE_INCIDENTS    = module.sqs.queue_urls["incidents"]
 #       SQS_QUEUE_DQ           = module.sqs.queue_urls["dq_checks"]
 #       SQS_QUEUE_COST         = module.sqs.queue_urls["cost_scan"]
 #       SQS_QUEUE_DAILY        = module.sqs.queue_urls["daily_sweep"]
 #       MCP_ORCHESTRATION_URL  = "http://${module.mcp_servers["orchestration-sfn"].service_name}.${var.environment}.local:8001"
 #       MCP_OBSERVABILITY_URL  = "http://${module.mcp_servers["observability-cloudwatch"].service_name}.${var.environment}.local:8002"
 #       MCP_DATA_EXECUTION_URL = "http://${module.mcp_servers["data-execution-glue-emr"].service_name}.${var.environment}.local:8003"
 #       MCP_DEVTOOLS_URL       = "http://${module.mcp_servers["devtools-github"].service_name}.${var.environment}.local:8007"
 #       DYNAMODB_REGISTRY      = module.dynamodb.table_names["workflow_registry"]
 #       DYNAMODB_INCIDENTS     = module.dynamodb.table_names["incidents"]
 #       S3_EVIDENCE_BUCKET     = module.s3.bucket_names["evidence"]
 #       LLM_PROVIDER           = var.llm_provider
 #     },
 #     var.llm_model != null && var.llm_model != "" ? { LLM_MODEL = var.llm_model } : {}
 #   )
 #
 #   secrets = local.llm_api_key_secret_arn != "" ? { LLM_API_KEY = local.llm_api_key_secret_arn } : {}
 # }
 #
 # # ECS: MCP Servers (orchestration-sfn, data-execution-glue-emr, observability-cloudwatch, devtools-github)
 # module "mcp_servers" {
 #   source = "./modules/ecs-service"
 #
 #   for_each = {
 #     "orchestration-sfn" = {
 #       port   = 8001
 #       cpu    = 256
 #       memory = 512
 #     }
 #     "data-execution-glue-emr" = {
 #       port   = 8003
 #       cpu    = 256
 #       memory = 512
 #     }
 #     "observability-cloudwatch" = {
 #       port   = 8002
 #       cpu    = 256
 #       memory = 512
 #     }
 #     "devtools-github" = {
 #       port   = 8007
 #       cpu    = 256
 #       memory = 512
 #     }
 #   }
 #
 #   name               = "mcp-${each.key}"
 #   environment        = var.environment
 #   cluster_id         = aws_ecs_cluster.main.id
 #   ecr_repository_uri = module.ecr.repository_uris["ops-autopilot/mcp-${each.key}"]
 #   task_role_arn      = module.iam.mcp_server_task_role_arns[each.key]
 #   execution_role_arn = module.iam.ecs_execution_role_arn
 #   log_group_name     = aws_cloudwatch_log_group.mcp_servers[each.key].name
 #
 #   service_registry_arn = aws_service_discovery_service.mcp[each.key].arn
 #
 #   cpu    = each.value.cpu
 #   memory = each.value.memory
 #
 #   desired_count = var.mcp_server_desired_count
 #
 #   container_port = each.value.port
 #
 #   subnet_ids         = module.vpc.private_subnet_ids
 #   security_group_ids = [module.vpc.ecs_security_group_id]
 #
 #   environment_variables = {
 #     HOST              = "0.0.0.0"
 #     PORT              = tostring(each.value.port)
 #     AWS_REGION        = var.aws_region
 #     ENVIRONMENT       = var.environment
 #     ALLOWLIST_ENABLED = "true"
 #     LOG_LEVEL         = "INFO"
 #   }
 # }





