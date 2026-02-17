locals {
  output_prefix = "${trimsuffix(var.output_prefix, "/")}/"
  job_name      = var.job_name != null && var.job_name != "" ? var.job_name : "${var.environment}-ops-autopilot-generate-electric-raw"
  role_name     = var.role_name != null && var.role_name != "" ? var.role_name : "${var.environment}-ops-autopilot-glue-generate-raw"
}

resource "aws_s3_object" "script" {
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.script_source_path
  etag   = filemd5(var.script_source_path)
}

resource "aws_iam_role" "glue" {
  name = local.role_name

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

data "aws_iam_policy_document" "glue_s3" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload"
    ]
    resources = [
      "arn:aws:s3:::${var.data_bucket_name}",
      "arn:aws:s3:::${var.data_bucket_name}/*"
    ]
  }

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

resource "aws_iam_role_policy" "glue_s3" {
  name   = "s3-access"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_s3.json
}

resource "aws_glue_job" "generate_raw" {
  name         = local.job_name
  role_arn     = aws_iam_role.glue.arn
  glue_version = var.glue_version

  command {
    name            = "glueetl"
    script_location = "s3://${var.script_bucket_name}/${aws_s3_object.script.key}"
    python_version  = "3"
  }

  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers

  default_arguments = {
    "--job-language"              = "python"
    "--output-bucket"             = var.data_bucket_name
    "--output-prefix"             = local.output_prefix
    "--max-rows"                  = tostring(var.max_rows)
    "--tables"                    = var.tables
    "--additional-python-modules" = "pandas,pyarrow,s3fs"
  }
}
