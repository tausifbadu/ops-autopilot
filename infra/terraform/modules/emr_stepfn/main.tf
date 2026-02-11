locals {
  input_prefix  = "${trimsuffix(var.input_prefix, "/")}/"
  output_prefix = "${trimsuffix(var.output_prefix, "/")}/"
  log_prefix    = "${trimsuffix(var.log_prefix, "/")}/"

  input_path  = "s3://${var.data_bucket_name}/${local.input_prefix}"
  output_path = "s3://${var.data_bucket_name}/${local.output_prefix}"
  log_uri     = "s3://${var.data_bucket_name}/${local.log_prefix}"

  cluster_name = var.cluster_name != null && var.cluster_name != "" ? var.cluster_name : "${var.environment}-ops-autopilot-emr"
  step_name    = var.step_name != null && var.step_name != "" ? var.step_name : "${var.environment}-ops-autopilot-emr-csv-to-parquet"
  sfn_name     = var.state_machine_name != null && var.state_machine_name != "" ? var.state_machine_name : "${var.environment}-ops-autopilot-emr-stepfn"
}

resource "aws_s3_object" "script" {
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.script_source_path
  etag   = filemd5(var.script_source_path)
}

resource "aws_iam_role" "emr_service" {
  name = "${var.environment}-ops-autopilot-emr-service"

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
  name = "${var.environment}-ops-autopilot-emr-ec2"

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

resource "aws_iam_role_policy" "emr_ec2_s3" {
  name   = "s3-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_s3.json
}

data "aws_iam_policy_document" "emr_ec2_s3" {
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

resource "aws_iam_instance_profile" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-ec2"
  role = aws_iam_role.emr_ec2.name
}

data "aws_iam_policy_document" "sfn_emr" {
  statement {
    effect = "Allow"
    actions = [
      "elasticmapreduce:RunJobFlow",
      "elasticmapreduce:AddJobFlowSteps",
      "elasticmapreduce:DescribeCluster",
      "elasticmapreduce:DescribeStep",
      "elasticmapreduce:TerminateJobFlows"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      aws_iam_role.emr_service.arn,
      aws_iam_role.emr_ec2.arn
    ]
  }
}

module "stepfn" {
  source = "../stepfn_common"

  name       = local.sfn_name
  definition = jsonencode({
    StartAt = "CreateCluster"
    States = {
      CreateCluster = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:createCluster"
        Parameters = {
          Name         = local.cluster_name
          ReleaseLabel = var.release_label
          Applications = [
            { Name = "Spark" }
          ]
          ServiceRole = aws_iam_role.emr_service.arn
          JobFlowRole = aws_iam_instance_profile.emr_ec2.name
          LogUri      = local.log_uri
          VisibleToAllUsers = true
          Configurations = [
            {
              Classification = "yarn-site"
              Properties = {
                "yarn.log-aggregation-enable" = "true"
                "yarn.log-aggregation.retain-seconds" = "604800"
              }
            }
          ]
          Instances = {
            Ec2SubnetId = var.subnet_id
            KeepJobFlowAliveWhenNoSteps = true
            InstanceGroups = [
              {
                Name          = "Master nodes"
                InstanceRole  = "MASTER"
                InstanceType  = var.master_instance_type
                InstanceCount = 1
                Market        = "ON_DEMAND"
              }
            ]
          }
        }
        ResultPath = "$.cluster"
        Next       = "AddStep"
      }
      AddStep = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
        Parameters = {
          "ClusterId.$" = "$.cluster.ClusterId"
          Step = {
            Name              = local.step_name
            ActionOnFailure   = "CONTINUE"
            HadoopJarStep = {
              Jar  = "command-runner.jar"
              Args = [
                "spark-submit",
                "--deploy-mode",
                "cluster",
                "s3://${var.script_bucket_name}/${aws_s3_object.script.key}",
                "--JOB_NAME",
                local.step_name,
                "--INPUT_PATH",
                local.input_path,
                "--OUTPUT_PATH",
                local.output_path
              ]
            }
          }
        }
        ResultPath = "$.step"
        End        = true
      }
    }
  })
  policy_json = data.aws_iam_policy_document.sfn_emr.json
  tags = {
    Name = local.sfn_name
  }
}
