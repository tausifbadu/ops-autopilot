# Multi-Region Deployment Guide

**Deploy Ops AutoPilot across multiple AWS regions with global state management**

---

## 🎯 Overview

This directory contains Terraform configurations for deploying Ops AutoPilot in a multi-region architecture:

- **Global Resources** (`global/`): DynamoDB Global Tables and Central S3 Evidence Bucket (deploy once)
- **Regional Resources** (`regional/`): ECS Services, SQS Queues, EventBridge Rules (deploy per region)

---

## 📋 Prerequisites

1. **Terraform >= 1.0**
2. **AWS CLI configured** with appropriate permissions
3. **Global resources deployed first** (DynamoDB tables, S3 bucket)
4. **List of operational regions** (e.g., `us-east-1`, `us-west-2`, `eu-west-1`)

---

## 🚀 Deployment Steps

### Step 1: Deploy Global Resources

Deploy global resources in the primary region (e.g., `us-east-1`):

```bash
cd infra/terraform/multi-region/global

# Initialize Terraform
terraform init

# Review plan
terraform plan \
  -var="environment=prod" \
  -var="primary_region=us-east-1" \
  -var="replica_regions=['us-west-2','eu-west-1','ap-southeast-1']"

# Apply
terraform apply
```

**Outputs** (save these for regional deployment):
- `dynamodb_table_names` - Table names for global tables
- `dynamodb_primary_region` - Primary region
- `s3_evidence_bucket` - Central S3 bucket name
- `s3_evidence_region` - S3 bucket region

### Step 2: Deploy Regional Resources

Deploy regional resources in each operational region:

```bash
cd infra/terraform/multi-region/regional

# Initialize Terraform
terraform init

# Create workspace for each region
terraform workspace new us-east-1
terraform workspace new us-west-2
terraform workspace new eu-west-1
# ... repeat for each region

# Select workspace
terraform workspace select us-east-1

# Review plan
terraform plan \
  -var="aws_region=us-east-1" \
  -var="environment=prod" \
  -var="global_dynamodb_tables.workflow_registry=prod-ops-autopilot-workflow-registry" \
  -var="global_dynamodb_tables.incidents=prod-ops-autopilot-incidents" \
  -var="global_dynamodb_tables.baselines=prod-ops-autopilot-baselines" \
  -var="global_s3_evidence_bucket=prod-ops-autopilot-evidence" \
  -var="dynamodb_primary_region=us-east-1" \
  -var="s3_evidence_region=us-east-1"

# Apply
terraform apply
```

**Repeat for each region** (us-west-2, eu-west-1, etc.)

---

## 📝 Using Terraform Workspaces

Terraform workspaces help manage multiple regional deployments:

```bash
# List workspaces
terraform workspace list

# Create workspace for a region
terraform workspace new us-west-2

# Select workspace
terraform workspace select us-west-2

# Deploy
terraform apply -var="aws_region=us-west-2" ...
```

---

## 🔧 Configuration

### Global Resources Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `environment` | Environment name | `prod` |
| `primary_region` | Primary region for global resources | `us-east-1` |
| `replica_regions` | List of replica regions | `["us-west-2", "eu-west-1"]` |
| `evidence_retention_days` | S3 evidence retention | `90` |
| `enable_s3_replication` | Enable S3 cross-region replication | `false` |

### Regional Resources Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `aws_region` | AWS region for deployment | Yes |
| `environment` | Environment name | Yes |
| `global_dynamodb_tables` | Global table names | Yes |
| `global_s3_evidence_bucket` | Global S3 bucket name | Yes |
| `dynamodb_primary_region` | Primary DynamoDB region | Yes |
| `s3_evidence_region` | S3 bucket region | Yes |

---

## 🔐 IAM Permissions

### Agent Host IAM Role

**Regional Permissions**:
- SQS: Read from regional queues
- ECS: Service discovery
- CloudWatch: Write logs

**Global Permissions**:
- DynamoDB: Read/Write to global tables (all regions)
- S3: Read/Write to central evidence bucket

### MCP Server IAM Roles

**Regional Permissions**:
- Step Functions: Regional access
- CloudWatch: Regional access
- Glue/EMR: Regional access
- ECS: Regional access

---

## 📊 Architecture

```
Global Resources (us-east-1)
├── DynamoDB Global Tables
│   ├── workflow_registry (replicated to all regions)
│   ├── incidents (replicated to all regions)
│   └── baselines (replicated to all regions)
└── S3 Evidence Bucket (central, accessible from all regions)

Regional Resources (per region)
├── ECS Cluster
├── Agent Host Service
├── MCP Server Services (8 servers)
├── SQS Queues (regional)
├── EventBridge Rules (regional)
└── VPC and Networking
```

---

## 🔄 Updating Global Resources

To add a new region to DynamoDB global tables:

1. Update `replica_regions` in `global/variables.tf`
2. Run `terraform apply` in `global/` directory
3. DynamoDB will automatically create replicas in new regions

---

## 🧹 Cleanup

### Remove Regional Deployment

```bash
cd infra/terraform/multi-region/regional
terraform workspace select us-west-2
terraform destroy -var="aws_region=us-west-2" ...
```

### Remove Global Resources

**⚠️ Warning**: This will delete all global state!

```bash
cd infra/terraform/multi-region/global
terraform destroy
```

---

## 📚 See Also

- [Multi-Region Architecture](docs/architecture/MULTI_REGION_DEPLOYMENT.md)
- [Main Terraform README](../README.md)
- [Deployment Guide](../../docs/DEPLOYMENT.md)

---

**Last Updated**: Current Session
