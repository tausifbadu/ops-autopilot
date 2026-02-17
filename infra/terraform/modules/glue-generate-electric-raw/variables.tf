variable "environment" {
  type = string
}

variable "script_bucket_name" {
  type        = string
  description = "S3 bucket for the Glue script."
}

variable "script_key" {
  type        = string
  default     = "glue-scripts/generate_electric_raw_glue.py"
  description = "S3 key for the Glue script."
}

variable "script_source_path" {
  type        = string
  description = "Local path to the Glue script."
}

variable "data_bucket_name" {
  type        = string
  description = "S3 bucket for raw data."
}

variable "output_prefix" {
  type        = string
  default     = "raw/electric-raw-dev"
  description = "S3 prefix for raw data output."
}

variable "max_rows" {
  type        = number
  default     = 10000
  description = "Max rows for non-meter_usage tables."
}

variable "tables" {
  type        = string
  default     = "all"
  description = "Comma-separated table names or 'all'."
}

variable "job_name" {
  type        = string
  default     = null
  description = "Override Glue job name."
}

variable "role_name" {
  type        = string
  default     = null
  description = "Override IAM role name for the Glue job role."
}

variable "glue_version" {
  type        = string
  default     = "4.0"
  description = "Glue version."
}

variable "worker_type" {
  type        = string
  default     = "G.1X"
  description = "Glue worker type."
}

variable "number_of_workers" {
  type        = number
  default     = 2
  description = "Number of Glue workers."
}
