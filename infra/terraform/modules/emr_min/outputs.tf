output "application_id" {
  value = aws_emrserverless_application.this.id
}

output "job_run_id" {
  value = aws_emrserverless_job_run.this.id
}
