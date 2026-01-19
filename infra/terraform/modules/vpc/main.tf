# VPC Module - Placeholder
# TODO: Implement VPC, subnets, NAT Gateway, security groups

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# Placeholder outputs - implement actual resources
output "vpc_id" {
  value = "vpc-placeholder"
}

output "private_subnet_ids" {
  value = ["subnet-placeholder"]
}

output "public_subnet_ids" {
  value = ["subnet-placeholder"]
}

output "ecs_security_group_id" {
  value = "sg-placeholder"
}

output "alb_security_group_id" {
  value = "sg-placeholder"
}
