# Pipeline Event Transformer Lambda
# Transforms EventBridge Glue/EMR failure events to PipelineFailureEvent JSON and sends to SQS.

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.lambda_source_path
  output_path = "${path.module}/pipeline-event-transformer.zip"
}

resource "aws_lambda_function" "transformer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.environment}-ops-autopilot-pipeline-event-transformer"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      SQS_QUEUE_URL = var.sqs_queue_url
      DEFAULT_TIER  = var.default_tier
    }
  }

  tags = {
    Name = "${var.environment}-pipeline-event-transformer"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.environment}-ops-autopilot-pipeline-event-transformer"

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

# CloudWatch Logs for Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to send messages to SQS
resource "aws_iam_role_policy" "lambda_sqs" {
  name   = "sqs-send"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_sqs.json
}

data "aws_iam_policy_document" "lambda_sqs" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage"
    ]
    resources = [var.sqs_queue_arn]
  }
}
