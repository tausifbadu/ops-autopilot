output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "agent_host_service_name" {
  description = "Agent Host service name"
  value       = module.agent_host.service_name
}

output "mcp_server_service_names" {
  description = "MCP server service names"
  value = {
    for k, v in module.mcp_servers : k => v.service_name
  }
}

output "sqs_queue_urls" {
  description = "SQS queue URLs"
  value       = module.sqs.queue_urls
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}
