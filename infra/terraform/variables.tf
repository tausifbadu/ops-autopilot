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
  description = "Default LLM provider (bedrock, openai, anthropic, gemini)"
  type        = string
  default     = "bedrock"
  
  validation {
    condition     = contains(["bedrock", "openai", "anthropic", "gemini"], var.llm_provider)
    error_message = "LLM provider must be bedrock, openai, anthropic, or gemini"
  }
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
