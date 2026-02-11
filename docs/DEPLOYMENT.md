# Deployment Guide - Local and AWS

This guide explains how to run ops-autopilot in both **local development** and **AWS production** environments.

## Architecture Overview

The solution is designed to work seamlessly in both environments:

### Local Development
- **MCP Servers**: Docker containers (via docker-compose)
- **Agent Host**: Runs directly with Python (no Docker)
- **Storage**: Local filesystem for evidence
- **Queues**: Optional (can process single events from files)

### AWS Production
- **MCP Servers**: ECS Fargate services
- **Agent Host**: ECS Fargate service (long-running)
- **Storage**: S3 for evidence, DynamoDB for state
- **Queues**: SQS for event processing

## Local Development Setup

### Prerequisites
- Python 3.11+
- Docker and docker-compose
- AWS credentials configured (`~/.aws/credentials`)

### Step 1: Start MCP Servers

```bash
# From project root
docker-compose up -d

# Verify they're running
docker-compose ps
curl http://localhost:8001/health
```

### Step 2: Run Agent Host Locally

```bash
cd agent-host

# Process a single event file
python -m agent_host.main --local-file ./src/agent_host/sample_events/pipeline_failure.json

# Or set environment variable
export LOCAL_EVENT_FILE=./src/agent_host/sample_events/pipeline_failure.json
python -m agent_host.main
```

### Local Configuration

Agent Host automatically detects local mode and uses:
- `http://localhost:8001` for MCP servers
- Local filesystem for evidence storage (`./evidence/`)
- No SQS polling (processes single events)

Environment variables (optional):
```bash
export MCP_ORCHESTRATION_URL=http://localhost:8001
export MCP_OBSERVABILITY_URL=http://localhost:8002
export AWS_REGION=us-east-1
export LLM_PROVIDER=openai  # or bedrock, anthropic, gemini
export LLM_API_KEY=your-api-key
```

## AWS Production Deployment

### Prerequisites
- AWS CLI configured
- Terraform >= 1.0
- Docker (for building images)

### Step 1: Deploy Infrastructure

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan -var="environment=prod"

# Deploy
terraform apply -var="environment=prod"
```

### Step 2: Build and Push Docker Images

**Windows:** Run the ECR login and `docker push` commands in **Command Prompt (CMD)**, not PowerShell. PowerShell can corrupt the ECR token (encoding/BOM) and cause "400 Bad Request" or "no basic auth credentials". Use CMD for a reliable login and push.

```bash
# Get ECR login (on Windows use CMD, not PowerShell)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push Agent Host
cd ../../agent-host
docker build -t ops-autopilot/agent-host .
docker tag ops-autopilot/agent-host:latest \
  <ecr-uri>/ops-autopilot/agent-host:latest
docker push <ecr-uri>/ops-autopilot/agent-host:latest

# Build and push MCP servers
cd ../mcp-servers/orchestration-sfn
docker build -t ops-autopilot/mcp-orchestration-sfn .
docker tag ops-autopilot/mcp-orchestration-sfn:latest \
  <ecr-uri>/ops-autopilot/mcp-orchestration-sfn:latest
docker push <ecr-uri>/ops-autopilot/mcp-orchestration-sfn:latest

# Repeat for other MCP servers...
```

### Step 3: Services Start Automatically

Once images are pushed, ECS services will:
1. Pull the latest images
2. Start tasks
3. Begin processing events from SQS

### AWS Configuration

Configuration is set via environment variables in ECS task definitions:

**Agent Host:**
- `ENVIRONMENT=prod` (or dev/staging)
- `AWS_REGION=us-east-1`
- `MCP_ORCHESTRATION_URL=http://mcp-orchestration-sfn:8001` (service discovery)
- `SQS_QUEUE_INCIDENTS=<queue-url>`
- `DYNAMODB_REGISTRY=<table-name>`
- `S3_EVIDENCE_BUCKET=<bucket-name>`
- `LLM_PROVIDER=bedrock`

**MCP Servers:**
- `HOST=0.0.0.0`
- `PORT=8001` (varies per server)
- `AWS_REGION=us-east-1`
- `ALLOWLIST_ENABLED=true`

## Environment Detection

The Agent Host automatically detects the environment:

### Local Mode Detection
- `ENVIRONMENT=local` (explicit)
- No ECS metadata endpoint
- No `AWS_EXECUTION_ENV` variable

### AWS Mode Detection
- `ENVIRONMENT=prod|dev|staging` (explicit)
- ECS metadata endpoint present
- `AWS_EXECUTION_ENV` variable set

## Key Differences

| Feature | Local | AWS |
|---------|-------|-----|
| **MCP Servers** | Docker containers (localhost) | ECS Fargate (service discovery) |
| **Agent Host** | Python directly | ECS Fargate service |
| **Event Source** | File or manual | SQS queues |
| **Storage** | Local filesystem | S3 + DynamoDB |
| **Scaling** | Single instance | Auto-scaling |
| **Monitoring** | Console logs | CloudWatch |

## Testing Locally Before AWS Deployment

1. **Test MCP servers locally:**
   ```bash
   docker-compose up
   curl http://localhost:8001/health
   ```

2. **Test Agent Host with local MCP servers:**
   ```bash
   cd agent-host
   python -m agent_host.main --local-file sample_events/pipeline_failure.json
   ```

3. **Verify evidence is created:**
   ```bash
   ls -la evidence/
   ```

4. **Deploy to AWS:**
   ```bash
   cd infra/terraform
   terraform apply
   ```

## Troubleshooting

### Local Issues

**MCP servers not accessible:**
- Check `docker-compose ps` - are containers running?
- Check ports: `netstat -an | grep 8001`
- Check logs: `docker-compose logs orchestration-sfn`

**Agent Host can't connect:**
- Verify MCP URLs: `echo $MCP_ORCHESTRATION_URL`
- Test connectivity: `curl http://localhost:8001/health`

### AWS Issues

**ECR login or push fails (400 Bad Request / no basic auth credentials):**
- On Windows, run `aws ecr get-login-password ... | docker login ...` and `docker push` in **Command Prompt (CMD)**, not PowerShell. Then push in the same CMD window.

**Services not starting:**
- Check ECS service events in AWS Console
- Check CloudWatch logs
- Verify ECR images are pushed
- Check IAM roles have correct permissions

**Service discovery not working:**
- Verify services are in same VPC
- Check security groups allow traffic
- Verify service names match DNS names

## Migration Path

1. **Develop locally** → Test with docker-compose
2. **Deploy to dev** → Test in AWS dev environment
3. **Deploy to prod** → Production deployment

Same code works in both environments! 🎉
