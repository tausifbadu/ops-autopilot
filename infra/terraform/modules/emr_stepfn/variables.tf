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
  default     = null
}

variable "script_s3_path" {
  type        = string
  default     = null
  description = "Full s3://... path to the EMR script when not uploading."
}

variable "upload_script" {
  type        = bool
  default     = true
  description = "If true, upload script from script_source_path; otherwise use script_s3_path."
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
  default     = "emr-6.15.0"
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

variable "step_args" {
  type        = list(string)
  default     = []
  description = "Additional arguments passed to spark-submit after the script path."
}

variable "second_step_enabled" {
  type        = bool
  default     = false
  description = "Enable a second EMR step in the same Step Function."
  validation {
    condition = !var.second_step_enabled || (
      var.second_upload_script ? (
        var.second_script_key != null && var.second_script_key != "" &&
        var.second_script_source_path != null && var.second_script_source_path != ""
      ) : (
        var.second_script_s3_path != null && var.second_script_s3_path != ""
      )
    )
    error_message = "When second_step_enabled is true, you must provide either second_script_key + second_script_source_path (if second_upload_script) or second_script_s3_path."
  }
}

variable "second_step_name" {
  type        = string
  default     = null
  description = "Override second EMR step name."
}

variable "second_step_args" {
  type        = list(string)
  default     = []
  description = "Arguments for the second EMR step."
}

variable "second_script_key" {
  type        = string
  default     = null
  description = "S3 key for the second EMR script."
}

variable "second_script_source_path" {
  type        = string
  default     = null
  description = "Local path to the second EMR script to upload."
}

variable "second_script_s3_path" {
  type        = string
  default     = null
  description = "Full s3://... path to the second EMR script when not uploading."
}

variable "second_upload_script" {
  type        = bool
  default     = true
  description = "If true, upload second script; otherwise use second_script_s3_path."
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
