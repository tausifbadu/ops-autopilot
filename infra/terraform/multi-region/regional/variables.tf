variable "aws_region" {
  description = "AWS region for this deployment"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "agent_host_cpu" {
  description = "CPU units for Agent Host (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "agent_host_memory" {
  description = "Memory for Agent Host in MB"
  type        = number
  default     = 4096
}

variable "agent_host_desired_count" {
  description = "Desired number of Agent Host tasks"
  type        = number
  default     = 2
}

variable "mcp_server_desired_count" {
  description = "Desired number of MCP server tasks"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "llm_provider" {
  description = "Default LLM provider"
  type        = string
  default     = "bedrock"
}

# Global resource references
variable "global_dynamodb_tables" {
  description = "Global DynamoDB table names (from global deployment)"
  type = object({
    workflow_registry = string
    incidents         = string
    baselines         = string
  })
}

variable "global_s3_evidence_bucket" {
  description = "Global S3 evidence bucket name (from global deployment)"
  type        = string
}

variable "dynamodb_primary_region" {
  description = "Primary region for DynamoDB global tables"
  type        = string
}

variable "s3_evidence_region" {
  description = "Region where S3 evidence bucket is located"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
