output "function_arn" {
  description = "ARN of the pipeline event transformer Lambda."
  value       = aws_lambda_function.transformer.arn
}

output "function_name" {
  description = "Name of the pipeline event transformer Lambda."
  value       = aws_lambda_function.transformer.function_name
}
