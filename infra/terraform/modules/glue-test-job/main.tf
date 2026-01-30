# Glue test job: fails on purpose to trigger EventBridge -> Lambda -> SQS
# Use this job in AWS Glue console or CLI to verify the failure pipeline.

# Upload script to S3 (Glue reads from S3)
resource "aws_s3_object" "script" {
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.script_source_path
  etag   = filemd5(var.script_source_path)
}

# IAM role for Glue (read script from S3, write logs to CloudWatch)
resource "aws_iam_role" "glue" {
  name = "${var.environment}-ops-autopilot-glue-test-job"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Allow Glue to read the script from S3
resource "aws_iam_role_policy" "glue_s3" {
  name   = "s3-script"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_s3.json
}

data "aws_iam_policy_document" "glue_s3" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.script_bucket_name}",
      "arn:aws:s3:::${var.script_bucket_name}/*"
    ]
  }
}

resource "aws_glue_job" "fail_for_test" {
  name         = "${var.environment}-ops-autopilot-fail-for-test"
  role_arn     = aws_iam_role.glue.arn
  max_retries  = 0  # fail once so we get one failure event
  max_capacity = 0.0625  # minimum DPU for Python shell (allowed: 0.0625 or 1.0)

  command {
    name            = "pythonshell"
    script_location = "s3://${var.script_bucket_name}/${aws_s3_object.script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language" = "python"
  }

  tags = {
    Name = "${var.environment}-ops-autopilot-fail-for-test"
  }
}
