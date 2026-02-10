variable "environment" {
  type = string
}

variable "script_bucket_name" {
  type        = string
  description = "S3 bucket where the EMR script is stored."
}

variable "script_key" {
  type        = string
  default     = "glue-scripts/csv_to_parquet.py"
  description = "S3 key for the EMR script."
}

variable "script_source_path" {
  type        = string
  description = "Local path to the EMR script to upload."
}

variable "data_bucket_name" {
  type        = string
  default     = "ops-autopilot-data"
  description = "S3 bucket containing input/output data."
}

variable "input_prefix" {
  type        = string
  default     = "raw/csv/"
  description = "Input prefix within the data bucket."
}

variable "output_prefix" {
  type        = string
  default     = "stage/parquet/"
  description = "Output prefix within the data bucket."
}

variable "log_prefix" {
  type        = string
  default     = "emr-logs/"
  description = "Log prefix within the data bucket."
}

variable "release_label" {
  type        = string
  default     = "emr-6.10.0"
  description = "EMR Serverless release label."
}

variable "application_name" {
  type        = string
  default     = null
  description = "Override EMR Serverless application name."
}

variable "job_name" {
  type        = string
  default     = null
  description = "Override EMR Serverless job name."
}

variable "driver_cpu" {
  type        = string
  default     = "1 vCPU"
  description = "Driver CPU."
}

variable "driver_memory" {
  type        = string
  default     = "2 GB"
  description = "Driver memory."
}

variable "driver_disk" {
  type        = string
  default     = "20 GB"
  description = "Driver disk."
}

variable "executor_cpu" {
  type        = string
  default     = "1 vCPU"
  description = "Executor CPU."
}

variable "executor_memory" {
  type        = string
  default     = "2 GB"
  description = "Executor memory."
}

variable "executor_disk" {
  type        = string
  default     = "20 GB"
  description = "Executor disk."
}
