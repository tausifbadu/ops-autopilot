# S3 Module - Creates S3 buckets

variable "environment" {
  type = string
}

resource "aws_s3_bucket" "evidence" {
  bucket = "${var.environment}-ops-autopilot-evidence"
  
  tags = {
    Name        = "${var.environment}-evidence-bucket"
    Environment = var.environment
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

    filter {}

    expiration {
      days = 90
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

output "bucket_names" {
  value = {
    evidence = aws_s3_bucket.evidence.bucket
  }
}
