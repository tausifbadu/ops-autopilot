variable "environment" {
  type = string
}

variable "script_bucket_name" {
  type        = string
  description = "S3 bucket name where the Glue script is stored."
}

variable "script_key" {
  type        = string
  default     = "glue-scripts/ops-autopilot-csv-to-parquet.py"
  description = "S3 key for the Glue script."
}

variable "script_source_path" {
  type        = string
  description = "Local path to the Python script file to upload."
}

variable "data_bucket_name" {
  type        = string
  default     = "ops-autopilot-data"
  description = "S3 bucket containing raw CSV and parquet outputs."
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

variable "temp_prefix" {
  type        = string
  default     = "tmp/glue/"
  description = "Temp directory prefix within the data bucket."
}

variable "job_name" {
  type        = string
  default     = null
  description = "Override Glue job name. Defaults to <environment>-ops-autopilot-csv-to-parquet."
}

variable "glue_version" {
  type        = string
  default     = "4.0"
  description = "Glue version for the Spark job."
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
