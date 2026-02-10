locals {
  input_prefix  = "${trimsuffix(var.input_prefix, "/")}/"
  output_prefix = "${trimsuffix(var.output_prefix, "/")}/"
  log_prefix    = "${trimsuffix(var.log_prefix, "/")}/"

  input_path  = "s3://${var.data_bucket_name}/${local.input_prefix}"
  output_path = "s3://${var.data_bucket_name}/${local.output_prefix}"
  log_uri     = "s3://${var.data_bucket_name}/${local.log_prefix}"

  application_name = var.application_name != null && var.application_name != "" ? var.application_name : "${var.environment}-ops-autopilot-emr-serverless"
  job_name         = var.job_name != null && var.job_name != "" ? var.job_name : "${var.environment}-ops-autopilot-emr-csv-to-parquet"
}

resource "aws_s3_object" "script" {
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.script_source_path
  etag   = filemd5(var.script_source_path)
}

resource "aws_iam_role" "emr_serverless" {
  name = "${var.environment}-ops-autopilot-emr-serverless"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "emr_serverless_s3" {
  name   = "s3-access"
  role   = aws_iam_role.emr_serverless.id
  policy = data.aws_iam_policy_document.emr_serverless_s3.json
}

data "aws_iam_policy_document" "emr_serverless_s3" {
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

resource "aws_emrserverless_application" "this" {
  name          = local.application_name
  release_label = var.release_label
  type          = "SPARK"

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }

  initial_capacity {
    initial_capacity_type = "Driver"
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = var.driver_cpu
        memory = var.driver_memory
        disk   = var.driver_disk
      }
    }
  }

  initial_capacity {
    initial_capacity_type = "Executor"
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = var.executor_cpu
        memory = var.executor_memory
        disk   = var.executor_disk
      }
    }
  }
}

resource "aws_emrserverless_job_run" "this" {
  name               = local.job_name
  application_id     = aws_emrserverless_application.this.id
  execution_role_arn = aws_iam_role.emr_serverless.arn
  execution_timeout  = 3600

  job_driver {
    spark_submit {
      entry_point = "s3://${var.script_bucket_name}/${aws_s3_object.script.key}"
      entry_point_arguments = [
        "--JOB_NAME",
        local.job_name,
        "--INPUT_PATH",
        local.input_path,
        "--OUTPUT_PATH",
        local.output_path
      ]
    }
  }

  configuration_overrides {
    monitoring_configuration {
      s3_monitoring_configuration {
        log_uri = local.log_uri
      }
    }
  }
}
