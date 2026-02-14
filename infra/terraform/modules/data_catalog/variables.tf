variable "data_bucket_name" {
  type        = string
  description = "Bucket for data and Athena results."
}

variable "database_name" {
  type        = string
  default     = "electric-raw-dev"
  description = "Glue database name."
}

variable "curated_database_name" {
  type        = string
  default     = "electric-curated-dev"
  description = "Glue database name for curated tables."
}
