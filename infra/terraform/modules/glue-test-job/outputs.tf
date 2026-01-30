output "job_name" {
  description = "Name of the Glue test job (use with aws glue start-job-run --job-name <name>)."
  value       = aws_glue_job.fail_for_test.name
}

output "script_s3_uri" {
  description = "S3 URI of the uploaded script."
  value       = "s3://${var.script_bucket_name}/${aws_s3_object.script.key}"
}
