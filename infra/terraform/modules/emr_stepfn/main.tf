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

  script_path = var.upload_script ? "s3://${var.script_bucket_name}/${var.script_key}" : var.script_s3_path
  step_args   = length(var.step_args) > 0 ? var.step_args : [
    "--JOB_NAME",
    local.step_name,
    "--INPUT_PATH",
    local.input_path,
    "--OUTPUT_PATH",
    local.output_path
  ]

  second_step_name = var.second_step_name != null && var.second_step_name != "" ? var.second_step_name : "${local.step_name}-step2"
  second_script_path = var.second_step_enabled ? (
    var.second_upload_script ? "s3://${var.script_bucket_name}/${var.second_script_key}" : var.second_script_s3_path
  ) : null
  has_second_step = var.second_step_enabled

  third_step_name = var.third_step_name != null && var.third_step_name != "" ? var.third_step_name : "${local.step_name}-step3"
  third_script_path = var.third_step_enabled ? (
    var.third_upload_script ? "s3://${var.script_bucket_name}/${var.third_script_key}" : var.third_script_s3_path
  ) : null
  has_third_step = var.third_step_enabled

  fourth_step_name = var.fourth_step_name != null && var.fourth_step_name != "" ? var.fourth_step_name : "${local.step_name}-step4"
  fourth_script_path = var.fourth_step_enabled ? (
    var.fourth_upload_script ? "s3://${var.script_bucket_name}/${var.fourth_script_key}" : var.fourth_script_s3_path
  ) : null
  has_fourth_step = var.fourth_step_enabled

  addstep2_task = {
    Type     = "Task"
    Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
    Parameters = {
      "ClusterId.$" = "$.cluster.ClusterId"
      Step = {
        Name            = local.second_step_name
        ActionOnFailure = "TERMINATE_CLUSTER"
        HadoopJarStep = {
          Jar  = "command-runner.jar"
          Args = concat(
            [
              "spark-submit",
              "--deploy-mode",
              "cluster",
              local.second_script_path
            ],
            var.second_step_args
          )
        }
      }
    }
    ResultPath = "$.step2"
    Next       = "AddStep3"
  }
  addstep2_pass = {
    Type = "Pass"
    Next = "AddStep3"
  }

  addstep2_state_map = jsondecode(
    local.has_second_step ? jsonencode({ AddStep2 = local.addstep2_task }) : jsonencode({ AddStep2 = local.addstep2_pass })
  )

  addstep3_task = {
    Type     = "Task"
    Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
    Parameters = {
      "ClusterId.$" = "$.cluster.ClusterId"
      Step = {
        Name            = local.third_step_name
        ActionOnFailure = "TERMINATE_CLUSTER"
        HadoopJarStep = {
          Jar  = "command-runner.jar"
          Args = concat(
            [
              "spark-submit",
              "--deploy-mode",
              "cluster",
              local.third_script_path
            ],
            var.third_step_args
          )
        }
      }
    }
    ResultPath = "$.step3"
    Next       = "AddStep4"
  }
  addstep3_pass = {
    Type = "Pass"
    Next = "AddStep4"
  }

  addstep3_state_map = jsondecode(
    local.has_third_step ? jsonencode({ AddStep3 = local.addstep3_task }) : jsonencode({ AddStep3 = local.addstep3_pass })
  )

  addstep4_task = {
    Type     = "Task"
    Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
    Parameters = {
      "ClusterId.$" = "$.cluster.ClusterId"
      Step = {
        Name            = local.fourth_step_name
        ActionOnFailure = "TERMINATE_CLUSTER"
        HadoopJarStep = {
          Jar  = "command-runner.jar"
          Args = concat(
            [
              "spark-submit",
              "--deploy-mode",
              "cluster",
              local.fourth_script_path
            ],
            var.fourth_step_args
          )
        }
      }
    }
    ResultPath = "$.step4"
    Next       = "TerminateCluster"
  }
  addstep4_pass = {
    Type = "Pass"
    Next = "TerminateCluster"
  }

  addstep4_state_map = jsondecode(
    local.has_fourth_step ? jsonencode({ AddStep4 = local.addstep4_task }) : jsonencode({ AddStep4 = local.addstep4_pass })
  )
}

resource "random_id" "emr_role_suffix" {
  keepers = {
    environment = var.environment
    sfn_name    = local.sfn_name
  }

  byte_length = 3
}

resource "aws_s3_object" "script" {
  count  = var.upload_script ? 1 : 0
  bucket = var.script_bucket_name
  key    = var.script_key
  source = var.upload_script ? var.script_source_path : null
  etag   = var.upload_script ? filemd5(var.script_source_path) : null
}

resource "aws_s3_object" "script2" {
  count  = var.second_step_enabled && var.second_upload_script ? 1 : 0
  bucket = var.script_bucket_name
  key    = var.second_script_key
  source = var.second_script_source_path
  etag   = filemd5(var.second_script_source_path)
}

resource "aws_s3_object" "script3" {
  count  = var.third_step_enabled && var.third_upload_script ? 1 : 0
  bucket = var.script_bucket_name
  key    = var.third_script_key
  source = var.third_script_source_path
  etag   = filemd5(var.third_script_source_path)
}

resource "aws_s3_object" "script4" {
  count  = var.fourth_step_enabled && var.fourth_upload_script ? 1 : 0
  bucket = var.script_bucket_name
  key    = var.fourth_script_key
  source = var.fourth_script_source_path
  etag   = filemd5(var.fourth_script_source_path)
}

resource "aws_iam_role" "emr_service" {
  name = "${var.environment}-ops-autopilot-emr-service-${random_id.emr_role_suffix.hex}"

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
  name = "${var.environment}-ops-autopilot-emr-ec2-${random_id.emr_role_suffix.hex}"

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

resource "aws_iam_role_policy" "emr_ec2_glue" {
  name   = "glue-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_glue.json
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

data "aws_iam_policy_document" "emr_ec2_glue" {
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:GetTableVersion",
      "glue:GetTableVersions"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_instance_profile" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-ec2-${random_id.emr_role_suffix.hex}"
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
    States = merge(
      {
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
              },
              {
                Classification = "hive-site"
                Properties = {
                  "hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
                }
              },
              {
                Classification = "spark-hive-site"
                Properties = {
                  "hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
                }
              },
              {
                Classification = "spark-defaults"
                Properties = {
                  "spark.sql.catalogImplementation" = "hive"
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
              Name            = local.step_name
              ActionOnFailure = "TERMINATE_CLUSTER"
              HadoopJarStep = {
                Jar  = "command-runner.jar"
                Args = concat(
                  [
                    "spark-submit",
                    "--deploy-mode",
                    "cluster",
                    local.script_path
                  ],
                  local.step_args
                )
              }
            }
          }
          ResultPath = "$.step"
          Next       = "AddStep2"
        }
      },
      local.addstep2_state_map,
      local.addstep3_state_map,
      local.addstep4_state_map,
      {
        TerminateCluster = {
          Type     = "Task"
          Resource = "arn:aws:states:::elasticmapreduce:terminateCluster"
          Parameters = {
            "ClusterId.$" = "$.cluster.ClusterId"
          }
          End = true
        }
      }
    )
  })
  policy_json = data.aws_iam_policy_document.sfn_emr.json
  tags = {
    Name = local.sfn_name
  }
}
