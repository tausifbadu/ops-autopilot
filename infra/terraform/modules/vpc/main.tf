# VPC Module - VPC, public subnets, and security groups for ECS Fargate (no NAT)

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name                                        = "${var.environment}-ops-autopilot-vpc"
    "for-use-with-amazon-emr-managed-policies"  = "true"
  }
}

# Internet Gateway (for public subnets - ECS tasks use this for ECR/AWS APIs)
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-ops-autopilot-igw"
  }
}

# Public subnets (ECS Fargate runs here with assign_public_ip for ECR pull / AWS APIs)
resource "aws_subnet" "public" {
  count = length(local.azs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                        = "${var.environment}-ops-autopilot-public-${local.azs[count.index]}"
    "for-use-with-amazon-emr-managed-policies"  = "true"
  }
}

# Route table -> IGW (no NAT)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.environment}-ops-autopilot-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security group for ECS tasks (egress all; ingress from same SG for service-to-service)
resource "aws_security_group" "ecs" {
  name        = "${var.environment}-ops-autopilot-ecs"
  description = "ECS Fargate - egress all, ingress from self"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "From same security group (MCP / agent-host)"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  tags = {
    Name = "${var.environment}-ops-autopilot-ecs-sg"
  }
}

# Placeholder for ALB SG if you add ALB later
resource "aws_security_group" "alb" {
  name        = "${var.environment}-ops-autopilot-alb"
  description = "ALB (placeholder)"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-ops-autopilot-alb-sg"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}

# ECS uses public subnets (no NAT; tasks get public IP for ECR/AWS APIs)
output "private_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}
