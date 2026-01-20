variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "primary_region" {
  description = "Primary AWS region for global resources"
  type        = string
  default     = "us-east-1"
}

variable "replica_regions" {
  description = "List of AWS regions for DynamoDB global table replicas"
  type        = list(string)
  default     = ["us-west-2", "eu-west-1"]
}

variable "evidence_retention_days" {
  description = "Number of days to retain evidence in S3"
  type        = number
  default     = 90
}

variable "enable_glacier_transition" {
  description = "Enable transition to Glacier after 30 days"
  type        = bool
  default     = false
}

variable "enable_s3_replication" {
  description = "Enable cross-region replication for S3 evidence bucket"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
