# EMR Studio Cluster Module
# Creates a persistent EMR on EC2 cluster (single node) with EMR Studio access for Jupyter notebooks

locals {
  cluster_name      = var.cluster_name != null && var.cluster_name != "" ? var.cluster_name : "${var.environment}-ops-autopilot-emr-studio"
  studio_name       = var.studio_name != null && var.studio_name != "" ? var.studio_name : "${var.environment}-ops-autopilot-studio"
  log_uri           = "s3://${var.data_bucket_name}/${trimsuffix(var.log_prefix, "/")}/"
  workspace_s3_path = "s3://${var.workspace_s3_bucket != null ? var.workspace_s3_bucket : var.data_bucket_name}/emr-studio-workspace/"
}

data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------
# EMR Cluster IAM Roles (Service Role and EC2 Instance Profile)
# -----------------------------------------------------------------

resource "aws_iam_role" "emr_service" {
  name = "${var.environment}-ops-autopilot-emr-studio-service"

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
    Name = "${var.environment}-emr-studio-service-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_service_role" {
  role       = aws_iam_role.emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

resource "aws_iam_role" "emr_ec2" {
  name = "${var.environment}-ops-autopilot-emr-studio-ec2"

  # EC2 for instance profile + self for EMR Studio runtime role (cluster assumes this role for sessions)
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
      {
        Sid    = "AllowAssumeRoleForRuntime"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.environment}-ops-autopilot-emr-studio-ec2"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })

  tags = {
    Name = "${var.environment}-emr-studio-ec2-role"
  }
}

# Allow instance profile to assume this role as runtime role (required for EMR Studio Runtime Role dropdown)
resource "aws_iam_role_policy" "emr_ec2_runtime_role" {
  name   = "allow-runtime-role-usage"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_ec2_assume_self.json
}

data "aws_iam_policy_document" "emr_ec2_assume_self" {
  statement {
    sid    = "AllowRuntimeRoleUsage"
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
      "sts:TagSession"
    ]
    resources = [aws_iam_role.emr_ec2.arn]
  }
}

resource "aws_iam_role_policy_attachment" "emr_ec2_role" {
  role       = aws_iam_role.emr_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

# S3 access for EMR EC2 instances (data, logs, workspace)
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
  name = "${var.environment}-ops-autopilot-emr-studio-ec2"
  role = aws_iam_role.emr_ec2.name

  tags = {
    Name = "${var.environment}-emr-studio-ec2-profile"
  }
}

# -----------------------------------------------------------------
# Security Groups for EMR Cluster and EMR Studio
# -----------------------------------------------------------------

resource "aws_security_group" "emr_master" {
  name        = "${var.environment}-ops-autopilot-emr-studio-master"
  description = "Security group for EMR Studio master node"
  vpc_id      = var.vpc_id

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Internal EMR communication"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  tags = {
    Name                                        = "${var.environment}-emr-studio-master-sg"
    "for-use-with-amazon-emr-managed-policies"  = "true"
  }
}

# EMR API requires slave SG when master SG is set (even with 0 core nodes)
resource "aws_security_group" "emr_slave" {
  name        = "${var.environment}-ops-autopilot-emr-studio-slave"
  description = "Security group for EMR core/task nodes (required by API; unused for single-node)"
  vpc_id      = var.vpc_id

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "From master"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    security_groups = [aws_security_group.emr_master.id]
  }

  ingress {
    description = "Self for worker communication"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  tags = {
    Name                                        = "${var.environment}-emr-studio-slave-sg"
    "for-use-with-amazon-emr-managed-policies"  = "true"
  }
}

resource "aws_security_group" "emr_studio" {
  name        = "${var.environment}-ops-autopilot-emr-studio-workspace"
  description = "Security group for EMR Studio Workspace"
  vpc_id      = var.vpc_id

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To EMR cluster"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.emr_master.id]
  }

  tags = {
    Name                                        = "${var.environment}-emr-studio-workspace-sg"
    "for-use-with-amazon-emr-managed-policies"  = "true"
  }
}

# Livy (required for notebook sessions)
resource "aws_security_group_rule" "emr_master_from_studio_18888" {
  type                     = "ingress"
  from_port                = 18888
  to_port                  = 18888
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.emr_studio.id
  security_group_id        = aws_security_group.emr_master.id
  description              = "Allow EMR Studio workspace to Livy on master"
}

# Full TCP from workspace to master (notebook, Spark UI, YARN, etc.)
resource "aws_security_group_rule" "emr_master_from_studio_all" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.emr_studio.id
  security_group_id        = aws_security_group.emr_master.id
  description              = "Allow EMR Studio workspace/notebook to master (all TCP)"
}

# Optional: if EMR uses a separate "notebook" SG (e.g. sg-0269917657894b560), add its ID here.
# Exclude the workspace SG so we don't duplicate the rule already added by emr_master_from_studio_all.
resource "aws_security_group_rule" "emr_master_from_notebook_sgs" {
  for_each = setsubtract(toset(var.notebook_security_group_ids), toset([aws_security_group.emr_studio.id]))

  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = each.value
  security_group_id        = aws_security_group.emr_master.id
  description              = "Allow EMR Studio notebook SG to master"
}

# -----------------------------------------------------------------
# EMR Security Configuration (required for Runtime Role in Studio)
# -----------------------------------------------------------------

resource "aws_emr_security_configuration" "runtime_role" {
  name = "${var.environment}-ops-autopilot-emr-studio-runtime-role"

  configuration = jsonencode({
    AuthorizationConfiguration = {
      IAMConfiguration = {
        EnableApplicationScopedIAMRole = true
      }
    }
  })
}

# -----------------------------------------------------------------
# EMR Cluster (EC2, single master node, persistent)
# -----------------------------------------------------------------

resource "aws_emr_cluster" "studio_cluster" {
  name                      = local.cluster_name
  release_label             = var.release_label
  applications              = ["Spark", "Livy", "JupyterEnterpriseGateway"]
  security_configuration    = aws_emr_security_configuration.runtime_role.name
  service_role              = aws_iam_role.emr_service.arn

  ec2_attributes {
    instance_profile                   = aws_iam_instance_profile.emr_ec2.arn
    subnet_id                          = var.subnet_id
    emr_managed_master_security_group  = aws_security_group.emr_master.id
    emr_managed_slave_security_group   = aws_security_group.emr_slave.id
    key_name                           = var.key_name
  }

  master_instance_group {
    instance_type  = var.master_instance_type
    instance_count = 1
  }

  log_uri = local.log_uri

  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false
  visible_to_all_users              = true

  configurations_json = jsonencode([
    {
      Classification = "yarn-site"
      Properties = {
        "yarn.log-aggregation-enable"        = "true"
        "yarn.log-aggregation.retain-seconds" = "604800"
      }
    },
    {
      Classification = "spark"
      Properties = {
        "maximizeResourceAllocation" = "true"
      }
    }
  ])

  tags = {
    Name = local.cluster_name
  }

  # Ensure EMR service role has managed policy attached before cluster starts (avoids "role is invalid")
  depends_on = [
    aws_iam_role_policy_attachment.emr_service_role,
    aws_iam_role_policy_attachment.emr_ec2_role
  ]
}

# -----------------------------------------------------------------
# EMR Studio IAM Roles
# -----------------------------------------------------------------

resource "aws_iam_role" "emr_studio_service" {
  name = "${var.environment}-ops-autopilot-emr-studio-workspace-service"

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
    Name = "${var.environment}-emr-studio-service-role"
  }
}

resource "aws_iam_role_policy" "emr_studio_service" {
  name   = "emr-studio-service-policy"
  role   = aws_iam_role.emr_studio_service.id
  policy = data.aws_iam_policy_document.emr_studio_service.json
}

# EMR Studio service role policy per AWS docs (required for workspace-to-cluster attachment)
# VPC, subnets, and security groups must be tagged: for-use-with-amazon-emr-managed-policies = true
data "aws_iam_policy_document" "emr_studio_service" {
  # S3 workspace storage
  statement {
    sid    = "AllowS3Workspace"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:GetEncryptionConfiguration",
      "s3:ListBucket",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${var.workspace_s3_bucket != null ? var.workspace_s3_bucket : var.data_bucket_name}/*",
      "arn:aws:s3:::${var.workspace_s3_bucket != null ? var.workspace_s3_bucket : var.data_bucket_name}"
    ]
  }

  # EMR read-only (establish channel to cluster)
  statement {
    sid    = "AllowEMRReadOnlyActions"
    effect = "Allow"
    actions = [
      "elasticmapreduce:ListInstances",
      "elasticmapreduce:DescribeCluster",
      "elasticmapreduce:ListSteps"
    ]
    resources = ["*"]
  }

  # EC2 ENI with EMR tag (required for workspace–cluster channel)
  statement {
    sid    = "AllowEC2ENIActionsWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterfacePermission",
      "ec2:DeleteNetworkInterface"
    ]
    resources = ["arn:aws:ec2:*:*:network-interface/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  statement {
    sid    = "AllowEC2ENIAttributeAction"
    effect = "Allow"
    actions = [
      "ec2:ModifyNetworkInterfaceAttribute"
    ]
    resources = [
      "arn:aws:ec2:*:*:instance/*",
      "arn:aws:ec2:*:*:network-interface/*",
      "arn:aws:ec2:*:*:security-group/*"
    ]
  }

  # Security group actions (tagged resources only)
  statement {
    sid    = "AllowEC2SecurityGroupActionsWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DeleteNetworkInterfacePermission"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  # CreateSecurityGroup with EMR tag (for default SGs EMR may create)
  statement {
    sid    = "AllowDefaultEC2SecurityGroupsCreationWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:CreateSecurityGroup"
    ]
    resources = ["arn:aws:ec2:*:*:security-group/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  statement {
    sid    = "AllowDefaultEC2SecurityGroupsCreationInVPCWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:CreateSecurityGroup"
    ]
    resources = ["arn:aws:ec2:*:*:vpc/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  statement {
    sid    = "AllowAddingEMRTagsDuringDefaultSecurityGroupCreation"
    effect = "Allow"
    actions = [
      "ec2:CreateTags"
    ]
    resources = ["arn:aws:ec2:*:*:security-group/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
    condition {
      test     = "StringEquals"
      variable = "ec2:CreateAction"
      values   = ["CreateSecurityGroup"]
    }
  }

  # ENI creation with EMR tag
  statement {
    sid    = "AllowEC2ENICreationWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface"
    ]
    resources = ["arn:aws:ec2:*:*:network-interface/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  statement {
    sid    = "AllowEC2ENICreationInSubnetAndSecurityGroupWithEMRTags"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface"
    ]
    resources = [
      "arn:aws:ec2:*:*:subnet/*",
      "arn:aws:ec2:*:*:security-group/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  statement {
    sid    = "AllowAddingTagsDuringEC2ENICreation"
    effect = "Allow"
    actions = [
      "ec2:CreateTags"
    ]
    resources = ["arn:aws:ec2:*:*:network-interface/*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:CreateAction"
      values   = ["CreateNetworkInterface"]
    }
  }

  # EC2 read-only
  statement {
    sid    = "AllowEC2ReadOnlyActions"
    effect = "Allow"
    actions = [
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeTags",
      "ec2:DescribeInstances",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcs"
    ]
    resources = ["*"]
  }

  # Secrets Manager (Git linking); tag condition optional for existing secrets
  statement {
    sid    = "AllowSecretsManagerReadOnlyActionsWithEMRTags"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/for-use-with-amazon-emr-managed-policies"
      values   = ["true"]
    }
  }

  # Allow GetSecretValue without tag for backwards compatibility (e.g. untagged secrets)
  statement {
    sid    = "AllowSecretsManagerGetSecretValue"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:*"]
  }

  # Workspace collaboration (IAM/SSO user lookup)
  statement {
    sid    = "AllowWorkspaceCollaboration"
    effect = "Allow"
    actions = [
      "iam:GetUser",
      "iam:GetRole",
      "iam:ListUsers",
      "iam:ListRoles",
      "sso:GetManagedApplicationInstance",
      "sso-directory:SearchUsers"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "emr_studio_user" {
  name = "${var.environment}-ops-autopilot-emr-studio-user"

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
    Name = "${var.environment}-emr-studio-user-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_studio_user_basic" {
  role       = aws_iam_role.emr_studio_user.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEMRFullAccessPolicy_v2"
}

# Session policy for Studio users (used by session mapping or Console)
resource "aws_iam_policy" "studio_session_policy" {
  name        = "${var.environment}-ops-autopilot-emr-studio-session"
  description = "Session policy for EMR Studio users"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticmapreduce:DescribeCluster",
          "elasticmapreduce:ListClusters",
          "elasticmapreduce:ListInstances",
          "elasticmapreduce:CreateEditor",
          "elasticmapreduce:DescribeEditor",
          "elasticmapreduce:ListEditors",
          "elasticmapreduce:StartEditor",
          "elasticmapreduce:StopEditor",
          "elasticmapreduce:DeleteEditor",
          "elasticmapreduce:OpenEditorInConsole"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.workspace_s3_bucket != null ? var.workspace_s3_bucket : var.data_bucket_name}/*",
          "arn:aws:s3:::${var.workspace_s3_bucket != null ? var.workspace_s3_bucket : var.data_bucket_name}"
        ]
      },
      # Required for Runtime Role dropdown in EMR Studio workspace (must allow GetClusterSessionCredentials for this role)
      {
        Sid      = "AllowRuntimeRoleInStudio"
        Effect   = "Allow"
        Action   = "elasticmapreduce:GetClusterSessionCredentials"
        Resource = "*"
        Condition = {
          StringEquals = {
            "elasticmapreduce:ExecutionRoleArn" = [aws_iam_role.emr_ec2.arn]
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.environment}-emr-studio-session-policy"
  }
}

# -----------------------------------------------------------------
# EMR Studio
# -----------------------------------------------------------------

resource "aws_emr_studio" "studio" {
  name                        = local.studio_name
  auth_mode                   = "IAM"
  vpc_id                      = var.vpc_id
  subnet_ids                  = var.studio_subnet_ids
  service_role                = aws_iam_role.emr_studio_service.arn
  # user_role not allowed when auth_mode = "IAM"; access is via IAM users/roles and session mappings
  workspace_security_group_id = aws_security_group.emr_studio.id
  engine_security_group_id    = aws_security_group.emr_master.id
  default_s3_location         = local.workspace_s3_path

  tags = {
    Name = local.studio_name
  }

  depends_on = [
    aws_emr_cluster.studio_cluster
  ]
}

# Session mappings: grant Studio access and session policy (Runtime Role dropdown) to users/groups via Terraform
locals {
  _legacy_mapping  = (var.studio_session_identity_id != null && var.studio_session_identity_id != "") ? [{ identity_type = "USER", identity_id = var.studio_session_identity_id }] : []
  _session_mappings = concat(local._legacy_mapping, var.studio_session_mappings)
  # AWS API requires exactly one of identity_id or identity_name; prefer identity_id when both set
  mappings_by_id   = { for i, m in local._session_mappings : "${m.identity_type}-${m.identity_id}" => m if try(m.identity_id, null) != null && try(m.identity_id, "") != "" }
  mappings_by_name = { for i, m in local._session_mappings : "${m.identity_type}-${m.identity_name}" => m if (try(m.identity_id, null) == null || try(m.identity_id, "") == "") && try(m.identity_name, null) != null && try(m.identity_name, "") != "" }
}

resource "aws_emr_studio_session_mapping" "by_id" {
  for_each = local.mappings_by_id

  studio_id          = aws_emr_studio.studio.id
  identity_type      = each.value.identity_type
  identity_id        = each.value.identity_id
  session_policy_arn = aws_iam_policy.studio_session_policy.arn
}

resource "aws_emr_studio_session_mapping" "by_name" {
  for_each = local.mappings_by_name

  studio_id          = aws_emr_studio.studio.id
  identity_type      = each.value.identity_type
  identity_name      = each.value.identity_name
  session_policy_arn = aws_iam_policy.studio_session_policy.arn
}
