# ECS Service Module
# Creates ECS Fargate service with task definition

variable "name" {
  description = "Service name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecr_repository_uri" {
  description = "ECR repository URI for Docker image"
  type        = string
}

variable "task_role_arn" {
  description = "IAM role ARN for task (for AWS API calls)"
  type        = string
}

variable "execution_role_arn" {
  description = "IAM role ARN for ECS task execution"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name"
  type        = string
}

variable "cpu" {
  description = "CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "subnet_ids" {
  description = "Subnet IDs for tasks"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "environment_variables" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets from AWS Secrets Manager or Parameter Store"
  type        = map(string)
  default     = {}
}

# ECS Task Definition
resource "aws_ecs_task_definition" "this" {
  family                   = "${var.environment}-${var.name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn      = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([{
    name  = var.name
    image = "${var.ecr_repository_uri}:latest"
    
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    
    environment = [
      for key, value in var.environment_variables : {
        name  = key
        value = value
      }
    ]
    
    secrets = [
      for key, value in var.secrets : {
        name      = key
        valueFrom = value
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
    
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = {
    Name        = "${var.environment}-${var.name}-task"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "this" {
  name            = "${var.environment}-${var.name}"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = true  # Public subnets, no NAT; needed for ECR pull / AWS APIs
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  health_check_grace_period_seconds = 60

  tags = {
    Name        = "${var.environment}-${var.name}"
    Environment = var.environment
  }
}

data "aws_region" "current" {}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.this.name
}

output "service_id" {
  description = "ECS service ID"
  value       = aws_ecs_service.this.id
}

output "task_definition_arn" {
  description = "Task definition ARN"
  value       = aws_ecs_task_definition.this.arn
}
