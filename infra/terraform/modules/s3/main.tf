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

# ---------------------------------------------------------------------------
# Scripts bucket: Lambda, Glue, EMR, etc. (deploy-time scripts, not evidence)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "scripts" {
  bucket = "${var.environment}-ops-autopilot-scripts"

  tags = {
    Name        = "${var.environment}-scripts-bucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_names" {
  value = {
    evidence = aws_s3_bucket.evidence.bucket
    scripts  = aws_s3_bucket.scripts.bucket
    data = aws_s3_bucket.ops_autopilot_storage.bucket
  }
}

resource "aws_s3_bucket" "ops_autopilot_storage" {
  bucket = "ops-autopilot-data"

  tags = {
    Name = "ops_autopilot_data_bucket"
  }
}

resource "aws_s3_bucket_notification" "ops_autopilot_storage_eventbridge" {
  bucket      = aws_s3_bucket.ops_autopilot_storage.id
  eventbridge = true
}

resource "aws_s3_object" "folders" {
  for_each = toset([
    "raw/",
    "curated/",
    "stage/",
    "stage/parquet/",
    "athena-results/"
  ])

  bucket = aws_s3_bucket.ops_autopilot_storage.id
  key    = each.value
}
