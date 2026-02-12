variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EMR cluster"
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC ID where EMR cluster will be created"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the EMR cluster (master node)"
  type        = string
}

variable "release_label" {
  description = "EMR release label (e.g., emr-6.15.0)"
  type        = string
  default     = "emr-6.15.0"
}

variable "master_instance_type" {
  description = "EC2 instance type for master node"
  type        = string
  default     = "m5.xlarge"
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH access"
  type        = string
  default     = null
}

variable "data_bucket_name" {
  description = "S3 bucket name for data"
  type        = string
}

variable "log_prefix" {
  description = "S3 prefix for EMR logs"
  type        = string
  default     = "emr-logs/"
}

variable "studio_name" {
  description = "Name of the EMR Studio"
  type        = string
  default     = null
}

variable "studio_subnet_ids" {
  description = "List of subnet IDs for EMR Studio (should be private or public subnets)"
  type        = list(string)
}

variable "workspace_s3_bucket" {
  description = "Optional S3 bucket for EMR Studio workspace storage. If not provided, will use data_bucket_name."
  type        = string
  default     = null
}

variable "studio_session_identity_id" {
  description = "Optional IAM user ID for a single session mapping (legacy). Prefer studio_session_mappings for multiple users/groups."
  type        = string
  default     = null
}

variable "studio_session_mappings" {
  description = "List of EMR Studio session mappings. Each identity gets the session policy (Runtime Role dropdown, workspace access). Use identity_id for IAM user ID (e.g. from aws iam get-user) or identity_name for IAM Identity Center."
  type = list(object({
    identity_type = string           # USER or GROUP
    identity_id   = optional(string) # IAM user/group unique ID (for IAM auth)
    identity_name = optional(string) # User/group name (for Identity Center)
  }))
  default = []
}

variable "notebook_security_group_ids" {
  description = "Optional list of security group IDs used by EMR Studio for notebooks. If attach fails with 'notebook security group sg-xxx does not have ingress', add that SG ID here (e.g. [\"sg-0269917657894b560\"])."
  type        = list(string)
  default     = []
}
