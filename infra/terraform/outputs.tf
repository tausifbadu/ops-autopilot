# ECS outputs - commented out while ECS is commented out in main.tf
# output "ecs_cluster_id" {
#   description = "ECS Cluster ID"
#   value       = aws_ecs_cluster.main.id
# }
# output "ecs_cluster_name" {
#   description = "ECS Cluster name"
#   value       = aws_ecs_cluster.main.name
# }
# output "agent_host_service_name" {
#   description = "Agent Host ECS service name"
#   value       = module.agent_host.service_name
# }
# output "mcp_server_service_names" {
#   description = "MCP server ECS service names"
#   value       = { for k, v in module.mcp_servers : k => v.service_name }
# }

# output "sqs_queue_urls" {
#   description = "SQS queue URLs"
#   value       = module.sqs.queue_urls
# }

output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "s3_bucket_names" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}

output "ecr_repository_uris" {
  description = "ECR repository URIs"
  value       = module.ecr.repository_uris
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}
