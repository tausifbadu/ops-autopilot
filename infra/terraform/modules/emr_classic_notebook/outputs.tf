output "cluster_id" {
  description = "EMR cluster ID (e.g. j-XXXXXXXXXXXXX)"
  value       = aws_emr_cluster.notebook.id
}

output "cluster_name" {
  description = "EMR cluster name"
  value       = aws_emr_cluster.notebook.name
}

output "master_public_dns" {
  description = "Master node public DNS (for SSH or web UI access)"
  value       = aws_emr_cluster.notebook.master_public_dns
}

output "log_uri" {
  description = "S3 log URI for the cluster"
  value       = local.log_uri
}

output "emr_service_role_arn" {
  description = "EMR service role ARN"
  value       = aws_iam_role.emr_service.arn
}

output "emr_ec2_role_arn" {
  description = "EMR EC2 instance role ARN"
  value       = aws_iam_role.emr_ec2.arn
}

output "emr_ec2_instance_profile_arn" {
  description = "EMR EC2 instance profile ARN"
  value       = aws_iam_instance_profile.emr_ec2.arn
}

output "master_security_group_id" {
  description = "Master node security group ID"
  value       = aws_security_group.emr_master.id
}

output "slave_security_group_id" {
  description = "Slave node security group ID"
  value       = aws_security_group.emr_slave.id
}

