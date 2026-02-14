output "job_name" {
  description = "Glue job name for generating raw electric data."
  value       = aws_glue_job.generate_raw.name
}
