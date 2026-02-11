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

## Remote state (S3 backend)

State is stored in S3. **Create the bucket once** before the first `terraform init`:

**PowerShell:**
```powershell
aws s3 mb s3://ops-autopilot-terraform-state --region us-east-1
```

**Bash:**
```bash
aws s3 mb s3://ops-autopilot-terraform-state --region us-east-1
```

If the bucket name is already taken (S3 names are global), use a unique name (e.g. `ops-autopilot-terraform-state-<account-id>`) and set the same name in `main.tf` in the `backend "s3"` block.

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

### Using OpenAI for Agent Host on ECS

To use OpenAI instead of Bedrock for the ECS agent-host:

**Option A – Terraform creates the secret (recommended)**  
Set your API key in Terraform; Terraform will create the Secrets Manager secret and use its ARN.

1. Set variables (e.g. in `terraform.tfvars`, **do not commit** – add `terraform.tfvars` to `.gitignore`):
   ```hcl
   llm_provider   = "openai"
   openai_api_key = "sk-your-openai-api-key"
   llm_model      = "gpt-4o"   # optional
   ```
   Or pass the key at apply time: `TF_VAR_openai_api_key="sk-..." terraform apply -var="llm_provider=openai"`

2. **Apply** and force a new ECS deployment (see step 3 below).

**Option B – Use an existing Secrets Manager secret**  
If you already created the secret (e.g. via AWS CLI):

1. Set Terraform variables:
   ```hcl
   llm_provider           = "openai"
   llm_api_key_secret_arn = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:dev/ops-autopilot/openai-api-key-xxxxx"
   llm_model              = "gpt-4o"   # optional
   ```

3. **Apply** and force a new ECS deployment so running tasks get the new env and secret:
   ```bash
   terraform apply
   aws ecs update-service --cluster dev-ops-autopilot-cluster --service dev-agent-host --force-new-deployment
   ```
   If the agent-host still uses Bedrock after switching to OpenAI, check startup logs for `LLM: LLM_PROVIDER env=...`; if env is `(not set)`, the task definition in use is old—force the deployment above and wait for the new task to start.

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
