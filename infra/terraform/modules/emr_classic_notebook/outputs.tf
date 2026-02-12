output "cluster_id" {
  value = aws_emr_cluster.notebook.id
}

output "master_public_dns" {
  value = aws_emr_cluster.notebook.master_public_dns
}
