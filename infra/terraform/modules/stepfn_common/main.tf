resource "aws_iam_role" "sfn" {
  name = "${var.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = var.assume_role_service
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "sfn" {
  name   = "${var.name}-policy"
  role   = aws_iam_role.sfn.id
  policy = var.policy_json
}

resource "aws_sfn_state_machine" "this" {
  name       = var.name
  role_arn   = aws_iam_role.sfn.arn
  definition = var.definition
  tags       = var.tags
}
