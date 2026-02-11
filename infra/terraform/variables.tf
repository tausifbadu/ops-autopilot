variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
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
  description = "CPU units for Agent Host (1024 = 1 vCPU). 256 = 0.25 vCPU (Fargate minimum)."
  type        = number
  default     = 256  # 0.25 vCPU (Fargate minimum; cost-optimized)
}

variable "agent_host_memory" {
  description = "Memory for Agent Host in MB. Must be valid Fargate pair with cpu (256 cpu = 512 MB only)."
  type        = number
  default     = 512  # 0.5 GB (Fargate minimum; cost-optimized)
}

variable "agent_host_desired_count" {
  description = "Desired number of Agent Host tasks. 1 = lower cost; 2+ for HA."
  type        = number
  default     = 1  # cost-optimized (was 2)
}

variable "mcp_server_desired_count" {
  description = "Desired number of MCP server tasks"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days. Lower = less storage cost."
  type        = number
  default     = 14  # cost-optimized (was 30)
}

variable "llm_provider" {
  description = "LLM provider for Agent Host (bedrock, openai, anthropic, gemini). Use openai for OpenAI on ECS."
  type        = string
  default     = "openai"
  
  validation {
    condition     = contains(["bedrock", "openai", "anthropic", "gemini"], var.llm_provider)
    error_message = "LLM provider must be bedrock, openai, anthropic, or gemini"
  }
}

variable "llm_api_key_secret_arn" {
  description = "ARN of existing Secrets Manager secret containing LLM API key. Leave null if using openai_api_key (Terraform will create the secret)."
  type        = string
  default     = null
}

variable "openai_api_key" {
  description = "OpenAI API key; if set, Terraform creates a Secrets Manager secret and ECS will use it. Prefer this over llm_api_key_secret_arn so Terraform manages the secret. Set via TF_VAR_openai_api_key or in a .tfvars file (do not commit)."
  type        = string
  default     = null
  sensitive   = true
}

variable "llm_model" {
  description = "Optional LLM model override (e.g. gpt-4o, gpt-4o-mini). Leave empty for provider default."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
