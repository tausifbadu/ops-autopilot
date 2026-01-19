# ALB Module - Optional Application Load Balancer
# Placeholder - implement if needed

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_groups" {
  type = list(string)
}

variable "mcp_services" {
  type = any
}

# Placeholder - implement ALB if enable_alb = true
output "dns_name" {
  value = "alb-placeholder"
}
