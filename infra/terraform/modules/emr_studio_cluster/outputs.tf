output "cluster_id" {
  description = "EMR cluster ID"
  value       = aws_emr_cluster.studio_cluster.id
}

output "cluster_name" {
  description = "EMR cluster name"
  value       = aws_emr_cluster.studio_cluster.name
}

output "cluster_master_public_dns" {
  description = "Public DNS of the EMR cluster master node"
  value       = aws_emr_cluster.studio_cluster.master_public_dns
}

output "studio_id" {
  description = "EMR Studio ID"
  value       = aws_emr_studio.studio.id
}

output "studio_url" {
  description = "EMR Studio URL"
  value       = aws_emr_studio.studio.url
}

output "studio_name" {
  description = "EMR Studio name"
  value       = aws_emr_studio.studio.name
}

output "emr_service_role_arn" {
  description = "ARN of the EMR service role"
  value       = aws_iam_role.emr_service.arn
}

output "emr_ec2_instance_profile_arn" {
  description = "ARN of the EMR EC2 instance profile"
  value       = aws_iam_instance_profile.emr_ec2.arn
}

output "emr_ec2_role_arn" {
  description = "ARN of the EMR EC2 role (use as execution role when attaching cluster in EMR Studio workspace)"
  value       = aws_iam_role.emr_ec2.arn
}

output "emr_studio_user_role_arn" {
  description = "ARN of the EMR Studio user role"
  value       = aws_iam_role.emr_studio_user.arn
}

output "log_uri" {
  description = "S3 URI for EMR logs"
  value       = local.log_uri
}

output "workspace_s3_path" {
  description = "S3 path for EMR Studio workspace"
  value       = local.workspace_s3_path
}
