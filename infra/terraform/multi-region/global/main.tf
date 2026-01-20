# Global Resources - Deploy once in primary region
# DynamoDB Global Tables and Central S3 Evidence Bucket

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.primary_region
  
  default_tags {
    tags = {
      Project     = "ops-autopilot"
      Environment = var.environment
      ManagedBy   = "terraform"
      ResourceType = "global"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}

# DynamoDB Global Tables
# Note: Global tables require creating the table first, then adding replicas
# This is a two-step process in Terraform

# Step 1: Create base table in primary region
# Note: For DynamoDB Global Tables v1, we need streams enabled
resource "aws_dynamodb_table" "workflow_registry" {
  name           = "${var.environment}-ops-autopilot-workflow-registry"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "workflow_name"
  
  attribute {
    name = "workflow_name"
    type = "S"
  }
  
  # Enable streams for global tables (required)
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  # Enable point-in-time recovery for global tables
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name        = "${var.environment}-workflow-registry"
    Environment = var.environment
    GlobalTable = "true"
  }
}

resource "aws_dynamodb_table" "incidents" {
  name           = "${var.environment}-ops-autopilot-incidents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "incident_id"
  
  attribute {
    name = "incident_id"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Enable streams for global tables (required)
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name        = "${var.environment}-incidents"
    Environment = var.environment
    GlobalTable = "true"
  }
}

resource "aws_dynamodb_table" "baselines" {
  name           = "${var.environment}-ops-autopilot-baselines"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "baseline_key"
  
  attribute {
    name = "baseline_key"
    type = "S"
  }
  
  # Enable streams for global tables (required)
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name        = "${var.environment}-baselines"
    Environment = var.environment
    GlobalTable = "true"
  }
}

# Step 2: Create global table replicas in other regions
resource "aws_dynamodb_global_table" "workflow_registry" {
  depends_on = [aws_dynamodb_table.workflow_registry]
  
  name = aws_dynamodb_table.workflow_registry.name
  
  replica {
    region_name = var.primary_region
  }
  
  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name = replica.value
    }
  }
}

resource "aws_dynamodb_global_table" "incidents" {
  depends_on = [aws_dynamodb_table.incidents]
  
  name = aws_dynamodb_table.incidents.name
  
  replica {
    region_name = var.primary_region
  }
  
  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name = replica.value
    }
  }
}

resource "aws_dynamodb_global_table" "baselines" {
  depends_on = [aws_dynamodb_table.baselines]
  
  name = aws_dynamodb_table.baselines.name
  
  replica {
    region_name = var.primary_region
  }
  
  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name = replica.value
    }
  }
}

# Central S3 Evidence Bucket
resource "aws_s3_bucket" "evidence" {
  bucket = "${var.environment}-ops-autopilot-evidence"
  
  tags = {
    Name        = "${var.environment}-evidence-bucket"
    Environment = var.environment
    GlobalBucket = "true"
  }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  
  rule {
    id     = "delete-old-evidence"
    status = "Enabled"
    
    expiration {
      days = var.evidence_retention_days
    }
  }
  
  # Optional: Transition to Glacier after 30 days
  rule {
    id     = "transition-to-glacier"
    status = var.enable_glacier_transition ? "Enabled" : "Disabled"
    
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Optional: Cross-region replication for disaster recovery
resource "aws_s3_bucket_replication_configuration" "evidence" {
  count = var.enable_s3_replication ? 1 : 0
  
  role   = aws_iam_role.s3_replication[0].arn
  bucket = aws_s3_bucket.evidence.id
  
  rule {
    id     = "replicate-to-backup-region"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.evidence_backup[0].arn
      storage_class = "STANDARD"
    }
  }
}

# Backup bucket for replication (optional)
resource "aws_s3_bucket" "evidence_backup" {
  count  = var.enable_s3_replication ? 1 : 0
  bucket = "${var.environment}-ops-autopilot-evidence-backup"
  
  tags = {
    Name        = "${var.environment}-evidence-backup-bucket"
    Environment = var.environment
    GlobalBucket = "true"
  }
}

# IAM role for S3 replication
resource "aws_iam_role" "s3_replication" {
  count = var.enable_s3_replication ? 1 : 0
  
  name = "${var.environment}-ops-autopilot-s3-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "s3_replication" {
  count = var.enable_s3_replication ? 1 : 0
  
  role = aws_iam_role.s3_replication[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.evidence.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersion",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = [
          "${aws_s3_bucket.evidence.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = [
          "${aws_s3_bucket.evidence_backup[0].arn}/*"
        ]
      }
    ]
  })
}
