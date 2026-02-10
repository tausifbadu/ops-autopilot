locals {
  input_prefix  = "${trimsuffix(var.input_prefix, "/")}/"
  output_prefix = "${trimsuffix(var.output_prefix, "/")}/"
  temp_prefix   = "${trimsuffix(var.temp_prefix, "/")}/"

  input_path  = "s3://${var.data_bucket_name}/${local.input_prefix}"
  output_path = "s3://${var.data_bucket_name}/${local.output_prefix}"
  temp_path   = "s3://${var.data_bucket_name}/${local.temp_prefix}"

  job_name = trimspace(var.job_name != null && var.job_name != "" ? var.job_name : "${var.environment}-ops-autopilot-csv-to-parquet")
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Upload script to S3 (Glue reads from S3)
resource "aws_s3_object" "script" {
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.script_source_path
  etag   = filemd5(var.script_source_path)
}

# IAM role for Glue (read script from S3, read/write data bucket, write logs)
resource "aws_iam_role" "glue" {
  name = "${var.environment}-ops-autopilot-glue-csv-parquet"

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

resource "aws_iam_role_policy" "glue_s3" {
  name   = "s3-access"
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
}

resource "aws_glue_job" "csv_to_parquet" {
  name         = local.job_name
  role_arn     = aws_iam_role.glue.arn
  glue_version = var.glue_version

  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers

  command {
    name            = "glueetl"
    script_location = "s3://${var.script_bucket_name}/${aws_s3_object.script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language" = "python"
    "--INPUT_PATH"   = local.input_path
    "--OUTPUT_PATH"  = local.output_path
    "--TempDir"      = local.temp_path
  }

  tags = {
    Name = local.job_name
  }
}

# EventBridge rule: trigger Glue job when new CSVs land in raw/csv/
resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name        = "${var.environment}-ops-autopilot-csv-created"
  description = "Trigger Glue CSV->Parquet job on new raw/csv objects."

  event_pattern = jsonencode({
    source      = ["aws.s3"],
    "detail-type" = ["Object Created"],
    detail = {
      bucket = {
        name = [var.data_bucket_name]
      },
      object = {
        key = [
          {
            prefix = local.input_prefix
          }
        ]
      }
    }
  })
}

data "archive_file" "glue_trigger_zip" {
  type        = "zip"
  source_file = "${path.root}/lambda/glue-trigger/handler.py"
  output_path = "${path.module}/glue-trigger.zip"
}

resource "random_id" "glue_trigger_suffix" {
  byte_length = 2
}

resource "aws_iam_role" "glue_trigger" {
  name = "${var.environment}-ops-autopilot-glue-trigger-${random_id.glue_trigger_suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_trigger_basic" {
  role       = aws_iam_role.glue_trigger.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "glue_trigger_start_job" {
  name   = "glue-start-job"
  role   = aws_iam_role.glue_trigger.id
  policy = data.aws_iam_policy_document.glue_trigger_start_job.json
}

data "aws_iam_policy_document" "glue_trigger_start_job" {
  statement {
    effect = "Allow"
    actions = [
      "glue:StartJobRun"
    ]
    resources = [
      aws_glue_job.csv_to_parquet.arn
    ]
  }
}

resource "aws_lambda_function" "glue_trigger" {
  function_name = "${var.environment}-ops-autopilot-glue-trigger"
  role          = aws_iam_role.glue_trigger.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.glue_trigger_zip.output_path
  source_code_hash = data.archive_file.glue_trigger_zip.output_base64sha256

  environment {
    variables = {
      GLUE_JOB_NAME = local.job_name
      INPUT_PATH    = local.input_path
      OUTPUT_PATH   = local.output_path
      TEMP_DIR      = local.temp_path
    }
  }
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.glue_trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_object_created.arn
}

resource "aws_cloudwatch_event_target" "glue_job" {
  rule = aws_cloudwatch_event_rule.s3_object_created.name
  arn  = aws_lambda_function.glue_trigger.arn
}
