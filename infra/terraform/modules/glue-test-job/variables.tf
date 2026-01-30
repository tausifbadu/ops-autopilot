variable "environment" {
  type = string
}

variable "script_bucket_name" {
  type        = string
  description = "S3 bucket name where the Glue script is stored (e.g. evidence bucket)."
}

variable "script_key" {
  type        = string
  default     = "glue-scripts/ops-autopilot-fail-for-test.py"
  description = "S3 key for the Glue test script."
}

variable "script_source_path" {
  type        = string
  description = "Local path to the Python script file to upload (e.g. path.root/glue-scripts/ops-autopilot-fail-for-test.py)."
}
