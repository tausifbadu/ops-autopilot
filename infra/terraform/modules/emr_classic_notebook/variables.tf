variable "environment" {
  type = string
}

variable "release_label" {
  type        = string
  default     = "emr-6.10.0"
  description = "EMR release label."
}

variable "cluster_name" {
  type        = string
  default     = null
  description = "Override cluster name."
}

variable "master_instance_type" {
  type        = string
  default     = "m5.xlarge"
  description = "Master instance type."
}

variable "core_instance_count" {
  type        = number
  default     = 0
  description = "Number of core nodes."
}

variable "subnet_id" {
  type        = string
  description = "Subnet for the EMR cluster."
}

variable "log_uri" {
  type        = string
  default     = "s3://ops-autopilot-data/emr-logs/"
  description = "S3 log URI."
}

variable "keep_cluster_alive" {
  type        = bool
  default     = true
  description = "Keep cluster alive when no steps."
}
