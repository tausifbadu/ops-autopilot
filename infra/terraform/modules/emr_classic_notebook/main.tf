# EMR Classic Notebook Module
# Creates a persistent EMR on EC2 cluster (single master node) with Spark, Livy,
# JupyterEnterpriseGateway, and JupyterHub. Access notebooks via JupyterHub (SSH tunnel to master).

data "aws_caller_identity" "current" {}

locals {
  cluster_name  = var.cluster_name != null && var.cluster_name != "" ? var.cluster_name : "${var.environment}-ops-autopilot-emr-notebook"
  log_uri       = "s3://${var.data_bucket_name}/${trimsuffix(var.log_prefix, "/")}/"
  ec2_role_name = "${var.environment}-ops-autopilot-emr-notebook-ec2"
}

# -----------------------------------------------------------------
# IAM: EMR Service Role
# -----------------------------------------------------------------

resource "aws_iam_role" "emr_service" {
  name = "${var.environment}-ops-autopilot-emr-notebook-service"

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

  tags = {
    Name = "${var.environment}-emr-notebook-service-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_service_role" {
  role       = aws_iam_role.emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

# -----------------------------------------------------------------
# IAM: EC2 Instance Role + Instance Profile
# -----------------------------------------------------------------

resource "aws_iam_role" "emr_ec2" {
  name = local.ec2_role_name

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

  tags = {
    Name = "${var.environment}-emr-notebook-ec2-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_ec2_role" {
  role       = aws_iam_role.emr_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

# S3 full access for data bucket (read/write data, logs, temp files)
resource "aws_iam_role_policy" "emr_ec2_s3" {
  name   = "s3-data-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_s3.json
}

data "aws_iam_policy_document" "emr_ec2_s3" {
  statement {
    sid    = "S3DataAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
      "s3:ListBucketMultipartUploads",
      "s3:GetBucketAcl"
    ]
    resources = [
      "arn:aws:s3:::${var.data_bucket_name}",
      "arn:aws:s3:::${var.data_bucket_name}/*"
    ]
  }
}

# Glue Data Catalog full access (read + write for Spark SQL CREATE/DROP/ALTER TABLE)
resource "aws_iam_role_policy" "emr_ec2_glue" {
  name   = "glue-catalog-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_glue.json
}

data "aws_iam_policy_document" "emr_ec2_glue" {
  # Read operations (query tables, list databases)
  statement {
    sid    = "GlueCatalogRead"
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:GetTableVersion",
      "glue:GetTableVersions",
      "glue:BatchGetPartition",
      "glue:GetCatalogImportStatus",
      "glue:GetConnection",
      "glue:GetConnections",
      "glue:SearchTables"
    ]
    resources = ["*"]
  }

  # Write operations (CREATE TABLE, DROP TABLE, ALTER TABLE, partition management)
  statement {
    sid    = "GlueCatalogWrite"
    effect = "Allow"
    actions = [
      "glue:CreateDatabase",
      "glue:UpdateDatabase",
      "glue:DeleteDatabase",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:DeleteTable",
      "glue:BatchDeleteTable",
      "glue:CreatePartition",
      "glue:UpdatePartition",
      "glue:DeletePartition",
      "glue:BatchCreatePartition",
      "glue:BatchDeletePartition",
      "glue:BatchUpdatePartition"
    ]
    resources = ["*"]
  }
}

# CloudWatch Logs (Spark driver/executor log output)
resource "aws_iam_role_policy" "emr_ec2_logs" {
  name   = "cloudwatch-logs-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_logs.json
}

data "aws_iam_policy_document" "emr_ec2_logs" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:GetLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_instance_profile" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-notebook-ec2"
  role = aws_iam_role.emr_ec2.name

  tags = {
    Name = "${var.environment}-emr-notebook-ec2-profile"
  }
}

# Runtime roles (EnableApplicationScopedIAMRole) are not used: they only support
# Spark, Hive, Livy, Presto. JupyterEnterpriseGateway and JupyterHub are not
# supported with runtime roles, so we omit the security configuration. Notebooks
# use the cluster EC2 instance profile for S3/Glue access.

# -----------------------------------------------------------------
# Security Groups
# revoke_rules_on_delete = true prevents the circular-dependency
# issue where EMR-added cross-SG rules block Terraform destroy.
# -----------------------------------------------------------------

# Master SG: only egress is managed here. Ingress is left to EMR (self/slave rules)
# and to aws_security_group_rule below (e.g. SSH). This avoids
# InvalidPermission.NotFound when Terraform tries to revoke rules that EMR
# merged with other sources into a single rule.
resource "aws_security_group" "emr_master" {
  name        = "${var.environment}-ops-autopilot-emr-notebook-master"
  description = "Security group for EMR Notebook master node"
  vpc_id      = var.vpc_id

  revoke_rules_on_delete = true

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    ignore_changes = [ingress]
  }

  tags = {
    Name                                       = "${var.environment}-emr-notebook-master-sg"
    "for-use-with-amazon-emr-managed-policies" = "true"
  }
}

# EMR API requires a slave SG even for single-node clusters
resource "aws_security_group" "emr_slave" {
  name        = "${var.environment}-ops-autopilot-emr-notebook-slave"
  description = "Security group for EMR core/task nodes (required by API; unused for single-node)"
  vpc_id      = var.vpc_id

  revoke_rules_on_delete = true

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name                                       = "${var.environment}-emr-notebook-slave-sg"
    "for-use-with-amazon-emr-managed-policies" = "true"
  }
}

# -----------------------------------------------------------------
# EMR Cluster
# Single-node m5.xlarge (master only) with Spark, Livy,
# JupyterEnterpriseGateway and JupyterHub 1.5.
# Hive metastore points to Glue Data Catalog so Spark SQL can
# query Glue tables directly.
# -----------------------------------------------------------------

resource "aws_emr_cluster" "notebook" {
  name          = local.cluster_name
  release_label = var.release_label
  applications  = ["Spark", "Livy", "JupyterEnterpriseGateway", "JupyterHub"]

  service_role = aws_iam_role.emr_service.arn
  log_uri      = local.log_uri

  ec2_attributes {
    subnet_id                         = var.subnet_id
    instance_profile                  = aws_iam_instance_profile.emr_ec2.arn
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave.id
    key_name                          = var.key_name
  }

  master_instance_group {
    instance_type  = var.master_instance_type
    instance_count = 1
  }

  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false
  visible_to_all_users              = true

  configurations_json = jsonencode([
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
    },
    {
      Classification = "spark"
      Properties = {
        "maximizeResourceAllocation" = "true"
      }
    },
    {
      Classification = "yarn-site"
      Properties = {
        "yarn.log-aggregation-enable"          = "true"
        "yarn.log-aggregation.retain-seconds"  = "604800"
      }
    }
  ])

  tags = {
    Name = local.cluster_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.emr_service_role,
    aws_iam_role_policy_attachment.emr_ec2_role
  ]
}

# Optional: SSH to master (for JupyterHub tunnel, debugging)
resource "aws_security_group_rule" "master_ssh" {
  count             = length(var.ssh_allowed_cidrs) > 0 ? 1 : 0
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = var.ssh_allowed_cidrs
  security_group_id = aws_security_group.emr_master.id
  description       = "SSH to master (JupyterHub tunnel, admin)"
}

