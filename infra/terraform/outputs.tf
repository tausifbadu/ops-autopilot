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

output "sqs_queue_urls" {
   description = "SQS queue URLs"
   value       = module.sqs.queue_urls
}

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

output "glue_test_job_name" {
  description = "Glue test job name (run with: aws glue start-job-run --job-name <this value>)"
  value       = module.glue_test_job.job_name
}

# EMR Studio Cluster
output "emr_studio_cluster_id" {
  description = "EMR Studio cluster ID"
  value       = module.emr_studio_cluster.cluster_id
}

output "emr_studio_url" {
  description = "EMR Studio URL for Jupyter notebooks"
  value       = module.emr_studio_cluster.studio_url
}

output "emr_studio_id" {
  description = "EMR Studio ID"
  value       = module.emr_studio_cluster.studio_id
}

output "emr_cluster_master_dns" {
  description = "EMR cluster master node public DNS"
  value       = module.emr_studio_cluster.cluster_master_public_dns
}

output "emr_studio_cluster_name" {
  description = "EMR cluster name (for attaching to workspace in EMR Studio)"
  value       = module.emr_studio_cluster.cluster_name
}

output "emr_studio_execution_role_arn" {
  description = "Execution role ARN to select in EMR Studio workspace (EC2 cluster role)"
  value       = module.emr_studio_cluster.emr_ec2_role_arn
}
