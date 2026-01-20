output "dynamodb_table_names" {
  description = "DynamoDB global table names"
  value = {
    workflow_registry = aws_dynamodb_table.workflow_registry.name
    incidents         = aws_dynamodb_table.incidents.name
    baselines         = aws_dynamodb_table.baselines.name
  }
}

output "dynamodb_primary_region" {
  description = "Primary region for DynamoDB global tables"
  value       = var.primary_region
}

output "dynamodb_replica_regions" {
  description = "Replica regions for DynamoDB global tables"
  value       = var.replica_regions
}

output "s3_evidence_bucket" {
  description = "Central S3 evidence bucket name"
  value       = aws_s3_bucket.evidence.bucket
}

output "s3_evidence_region" {
  description = "Region where S3 evidence bucket is located"
  value       = var.primary_region
}

output "s3_evidence_bucket_arn" {
  description = "ARN of the central S3 evidence bucket"
  value       = aws_s3_bucket.evidence.arn
}
