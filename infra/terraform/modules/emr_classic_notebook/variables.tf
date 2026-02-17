variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for EMR security groups."
}

variable "subnet_id" {
  type        = string
  description = "Subnet for the EMR master node. Use a public subnet if you need direct SSH/web access."
}

variable "data_bucket_name" {
  type        = string
  description = "S3 bucket for data, logs, and notebook workspace storage."
}

variable "log_prefix" {
  type        = string
  default     = "emr-notebook-logs/"
  description = "S3 prefix within data_bucket_name for EMR logs."
}

variable "cluster_name" {
  type        = string
  default     = null
  description = "Override cluster name. Defaults to {environment}-ops-autopilot-emr-notebook."
}

variable "release_label" {
  type        = string
  default     = "emr-6.15.0"
  description = "EMR release label."
}

variable "master_instance_type" {
  type        = string
  default     = "m5.xlarge"
  description = "Master node instance type."
}

variable "key_name" {
  type        = string
  default     = null
  description = "EC2 key pair name for SSH access to the master node. Leave null to disable SSH."
}

variable "ssh_allowed_cidrs" {
  type        = list(string)
  default     = []
  description = "CIDR blocks allowed to SSH to the master (port 22). Set to [\"0.0.0.0/0\"] or your IP (e.g. [\"1.2.3.4/32\"]) for JupyterHub tunnel. Empty = no SSH from outside."
}
