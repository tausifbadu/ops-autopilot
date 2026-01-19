# Infrastructure as Code - Terraform

This directory contains Terraform configuration for deploying ops-autopilot to AWS using ECS Fargate.

## Architecture

- **ECS Fargate Cluster**: Runs Agent Host and MCP servers
- **ECR Repositories**: Stores Docker images
- **SQS Queues**: Event queues (incidents, DQ, cost, daily)
- **DynamoDB Tables**: State store (registry, incidents, baselines)
- **S3 Buckets**: Evidence storage
- **EventBridge Rules**: Event routing
- **IAM Roles**: Least-privilege access per service
- **VPC**: Networking with private subnets

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.0
3. Docker (for building images)

## Quick Start

### 1. Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### 2. Review and customize variables

Edit `terraform.tfvars` or set environment variables:

```bash
export TF_VAR_environment=dev
export TF_VAR_aws_region=us-east-1
export TF_VAR_llm_provider=bedrock
```

### 3. Plan deployment

```bash
terraform plan
```

### 4. Deploy infrastructure

```bash
terraform apply
```

## Building and Pushing Docker Images

After infrastructure is created, build and push Docker images:

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push Agent Host
cd ../../agent-host
docker build -t ops-autopilot/agent-host .
docker tag ops-autopilot/agent-host:latest <ecr-uri>/ops-autopilot/agent-host:latest
docker push <ecr-uri>/ops-autopilot/agent-host:latest

# Build and push MCP servers
cd ../mcp-servers/orchestration-sfn
docker build -t ops-autopilot/mcp-orchestration-sfn .
docker tag ops-autopilot/mcp-orchestration-sfn:latest <ecr-uri>/ops-autopilot/mcp-orchestration-sfn:latest
docker push <ecr-uri>/ops-autopilot/mcp-orchestration-sfn:latest
```

## Module Structure

- `modules/vpc/` - VPC, subnets, security groups
- `modules/ecr/` - ECR repositories
- `modules/sqs/` - SQS queues
- `modules/dynamodb/` - DynamoDB tables
- `modules/s3/` - S3 buckets
- `modules/iam/` - IAM roles and policies
- `modules/ecs-service/` - ECS Fargate service
- `modules/alb/` - Application Load Balancer (optional)
- `modules/eventbridge/` - EventBridge rules

## Variables

See `variables.tf` for all configurable variables.

Key variables:
- `environment` - Environment name (dev/staging/prod)
- `aws_region` - AWS region
- `agent_host_cpu` - Agent Host CPU (default: 2048 = 2 vCPU)
- `agent_host_memory` - Agent Host memory in MB (default: 4096 = 4 GB)
- `llm_provider` - Default LLM provider

## Outputs

After deployment, get outputs:

```bash
terraform output
```

Key outputs:
- ECS cluster ID and name
- Service names
- SQS queue URLs
- DynamoDB table names
- S3 bucket names
- ECR repository URIs

## Updating Services

After pushing new Docker images:

```bash
# Force new deployment
aws ecs update-service \
  --cluster <cluster-name> \
  --service <service-name> \
  --force-new-deployment
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all resources including data in DynamoDB and S3!

## Notes

- MCP servers communicate via service discovery (private DNS)
- Agent Host polls SQS queues continuously
- All services run in private subnets with NAT Gateway for internet access
- CloudWatch Container Insights enabled for monitoring
- Logs retained for 30 days (configurable)
