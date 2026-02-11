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
  description = "EMR release label."
}

variable "state_machine_name" {
  type        = string
  default     = null
  description = "Override Step Functions state machine name."
}

variable "cluster_name" {
  type        = string
  default     = null
  description = "Override EMR cluster name."
}

variable "step_name" {
  type        = string
  default     = null
  description = "Override EMR step name."
}

variable "master_instance_type" {
  type        = string
  default     = "m5.xlarge"
  description = "Master instance type."
}

variable "subnet_id" {
  type        = string
  description = "Subnet for the EMR cluster."
}
