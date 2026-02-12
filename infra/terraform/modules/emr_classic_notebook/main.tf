locals {
  cluster_name = var.cluster_name != null && var.cluster_name != "" ? var.cluster_name : "${var.environment}-ops-autopilot-emr-notebook"
}

resource "aws_iam_role" "emr_service" {
  name = "${var.environment}-ops-autopilot-emr-service-notebook"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "elasticmapreduce.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service_role" {
  role       = aws_iam_role.emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

resource "aws_iam_role" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-ec2-notebook"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_ec2_role" {
  role       = aws_iam_role.emr_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

resource "aws_iam_instance_profile" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-ec2-notebook"
  role = aws_iam_role.emr_ec2.name
}

resource "aws_emr_cluster" "notebook" {
  name          = local.cluster_name
  release_label = var.release_label
  applications  = ["Spark", "Livy"]

  service_role = aws_iam_role.emr_service.arn
  log_uri      = var.log_uri

  ec2_attributes {
    subnet_id        = var.subnet_id
    instance_profile = aws_iam_instance_profile.emr_ec2.name
  }

  keep_job_flow_alive_when_no_steps = var.keep_cluster_alive
  termination_protection            = false

  master_instance_group {
    instance_type  = var.master_instance_type
    instance_count = 1
  }

  dynamic "core_instance_group" {
    for_each = var.core_instance_count > 0 ? [1] : []
    content {
      instance_type  = var.master_instance_type
      instance_count = var.core_instance_count
    }
  }

  tags = {
    Name = local.cluster_name
  }
}
