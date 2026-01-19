# Infrastructure

This directory contains infrastructure-as-code for deploying ops-autopilot to AWS.

## Dual Environment Support

**✅ The solution works in BOTH local and AWS environments:**

### Local Development
- MCP Servers run in Docker containers (see `../docker-compose.yml`)
- Agent Host runs directly with Python
- Uses localhost URLs and local file storage
- Perfect for development and testing

### AWS Production
- MCP Servers run in ECS Fargate services
- Agent Host runs in ECS Fargate service
- Uses service discovery and AWS services (SQS, DynamoDB, S3)
- Production-ready, scalable deployment

**The same code works in both environments!** Environment detection is automatic.

## Quick Start

### Local Development
```bash
# Start MCP servers
docker-compose up -d

# Run Agent Host
cd agent-host
python -m agent_host.main --local-file sample_events/pipeline_failure.json
```

### AWS Deployment
```bash
# Deploy infrastructure
cd terraform
terraform init
terraform apply

# Build and push images (see terraform/README.md)
# Services start automatically
```

## Directory Structure

```
infra/
├── README.md           # This file
└── terraform/          # Terraform configuration
    ├── main.tf         # Main infrastructure
    ├── variables.tf    # Variables
    ├── outputs.tf      # Outputs
    └── modules/        # Reusable modules
        ├── ecs-service/    # ECS Fargate service
        ├── ecr/            # ECR repositories
        ├── sqs/            # SQS queues
        ├── dynamodb/       # DynamoDB tables
        ├── s3/             # S3 buckets
        ├── iam/            # IAM roles
        ├── vpc/            # VPC (placeholder)
        ├── alb/            # ALB (optional)
        └── eventbridge/    # EventBridge rules
```

## See Also

- `../docs/DEPLOYMENT.md` - Complete deployment guide
- `terraform/README.md` - Terraform-specific documentation
