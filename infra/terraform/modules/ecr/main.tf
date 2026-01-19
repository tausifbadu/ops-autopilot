# ECR Module - Creates ECR repositories

variable "repositories" {
  description = "List of ECR repository names"
  type        = list(string)
}

variable "environment" {
  type = string
}

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repositories)
  
  name                 = each.value
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "AES256"
  }
  
  tags = {
    Name        = each.value
    Environment = var.environment
  }
}

output "repository_uris" {
  value = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}
