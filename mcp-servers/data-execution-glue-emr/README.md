# Data Execution Glue/EMR MCP Server

MCP (Model Context Protocol) server for AWS Glue and EMR operations. Provides safe, typed, auditable tool APIs for interacting with Glue jobs and EMR clusters/steps.

## Overview

The Data Execution MCP Server enables the Agent Host to:
- Get Glue job run details and status
- List Glue job runs
- Get EMR step details and status
- List EMR steps
- Get EMR cluster information
- Map jobs/clusters to CloudWatch log groups

## Features

- ✅ **Glue Job Operations**: Get job runs, list runs, map to log groups
- ✅ **EMR Operations**: Get steps, list steps, get cluster details
- ✅ **Log Group Mapping**: Automatically map jobs/clusters to CloudWatch log groups
- ✅ **Resource Allowlist**: Security boundary to restrict access
- ✅ **Type-safe APIs**: Pydantic schemas for request/response validation
- ✅ **Structured Logging**: Consistent, auditable logging
- ✅ **Health Checks**: `/health` endpoint for monitoring

## Architecture

```
Agent Host
    ↓
MCP Client (HTTP)
    ↓
Data Execution MCP Server (FastAPI)
    ↓
AWS Glue & EMR (boto3)
```

## Tools

### Glue Tools

#### 1. `get_glue_job_run`

Get detailed information about a Glue job run.

**Request:**
```json
{
  "tool": "get_glue_job_run",
  "arguments": {
    "job_name": "my-glue-job",
    "run_id": "jr_abc123def456"
  }
}
```

**Response:**
```json
{
  "result": {
    "job_name": "my-glue-job",
    "run_id": "jr_abc123def456",
    "job_run_state": "FAILED",
    "started_on": "2024-01-15T10:00:00Z",
    "completed_on": "2024-01-15T10:05:00Z",
    "execution_time": 300,
    "error_message": "An error occurred while calling o1234.getDynamicFrame",
    "error_string": "An error occurred while calling o1234.getDynamicFrame",
    "allocated_capacity": 2,
    "glue_version": "3.0",
    "arguments": {
      "--enable-metrics": "true"
    },
    "log_group_name": "/aws-glue/jobs/my-glue-job"
  }
}
```

#### 2. `list_glue_job_runs`

List job runs for a Glue job.

**Request:**
```json
{
  "tool": "list_glue_job_runs",
  "arguments": {
    "job_name": "my-glue-job",
    "max_results": 100,
    "next_token": null
  }
}
```

**Response:**
```json
{
  "result": {
    "job_name": "my-glue-job",
    "job_runs": [
      {
        "Id": "jr_abc123",
        "JobRunState": "FAILED",
        "StartedOn": "2024-01-15T10:00:00Z",
        "CompletedOn": "2024-01-15T10:05:00Z"
      }
    ],
    "next_token": null
  }
}
```

#### 3. `get_log_groups_for_job`

Get CloudWatch log groups associated with a Glue job.

**Request:**
```json
{
  "tool": "get_log_groups_for_job",
  "arguments": {
    "job_name": "my-glue-job"
  }
}
```

**Response:**
```json
{
  "result": {
    "job_name": "my-glue-job",
    "log_groups": [
      "/aws-glue/jobs/my-glue-job",
      "/aws-glue/jobs/error/my-glue-job",
      "/aws-glue/jobs/output",
      "/aws-glue/jobs/error"
    ]
  }
}
```

### EMR Tools

#### 4. `get_emr_step`

Get detailed information about an EMR step.

**Request:**
```json
{
  "tool": "get_emr_step",
  "arguments": {
    "cluster_id": "j-ABC123DEF456",
    "step_id": "s-ABC123DEF456"
  }
}
```

**Response:**
```json
{
  "result": {
    "cluster_id": "j-ABC123DEF456",
    "step_id": "s-ABC123DEF456",
    "name": "Spark Step",
    "state": "FAILED",
    "state_change_reason": "Step failed with errors",
    "action_on_failure": "TERMINATE_CLUSTER",
    "started_on": "2024-01-15T10:00:00Z",
    "ended_on": "2024-01-15T10:10:00Z",
    "jar": "command-runner.jar",
    "main_class": null,
    "args": ["spark-submit", "--class", "Main", "s3://bucket/app.jar"],
    "properties": {}
  }
}
```

#### 5. `list_emr_steps`

List steps for an EMR cluster.

**Request:**
```json
{
  "tool": "list_emr_steps",
  "arguments": {
    "cluster_id": "j-ABC123DEF456",
    "step_states": ["FAILED", "COMPLETED"],
    "max_results": 100,
    "marker": null
  }
}
```

**Response:**
```json
{
  "result": {
    "cluster_id": "j-ABC123DEF456",
    "steps": [
      {
        "Id": "s-ABC123DEF456",
        "Name": "Spark Step",
        "Status": {
          "State": "FAILED",
          "StateChangeReason": {
            "Message": "Step failed with errors"
          }
        }
      }
    ],
    "marker": null
  }
}
```

#### 6. `get_emr_cluster`

Get EMR cluster details.

**Request:**
```json
{
  "tool": "get_emr_cluster",
  "arguments": {
    "cluster_id": "j-ABC123DEF456"
  }
}
```

**Response:**
```json
{
  "result": {
    "cluster_id": "j-ABC123DEF456",
    "name": "my-emr-cluster",
    "state": "TERMINATED",
    "state_change_reason": "Step failed",
    "release_label": "emr-6.15.0",
    "created_on": "2024-01-15T09:00:00Z",
    "ready_on": "2024-01-15T09:05:00Z",
    "ended_on": "2024-01-15T10:10:00Z",
    "log_uri": "s3://my-bucket/emr-logs/",
    "instance_count": "INSTANCE_FLEET"
  }
}
```

#### 7. `get_log_groups_for_cluster`

Get CloudWatch log groups associated with an EMR cluster.

**Request:**
```json
{
  "tool": "get_log_groups_for_cluster",
  "arguments": {
    "cluster_id": "j-ABC123DEF456"
  }
}
```

**Response:**
```json
{
  "result": {
    "cluster_id": "j-ABC123DEF456",
    "log_groups": [
      "/aws/emr/j-ABC123DEF456",
      "/aws/emr/j-ABC123DEF456/containers",
      "/aws/emr/containers"
    ]
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8003` |
| `AWS_REGION` | Default AWS region | `us-east-1` |
| `AWS_ENDPOINT_URL` | AWS endpoint URL (for local testing) | `None` |
| `ALLOWLIST_ENABLED` | Enable resource allowlist | `true` |
| `ALLOWLIST_FILE` | Path to allowlist file | `None` |
| `LOG_LEVEL` | Logging level | `INFO` |

### AWS Credentials

The server uses standard AWS credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (when running on ECS/EC2)

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetJob",
        "glue:GetJobRun",
        "glue:GetJobRuns",
        "glue:ListJobs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "emr:DescribeCluster",
        "emr:DescribeStep",
        "emr:ListSteps",
        "emr:ListClusters"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security

### Resource Allowlist

The server supports an allowlist to restrict access to specific Glue jobs and EMR clusters:

```python
# In allowlist.py
allowlist.add_glue_job("my-glue-job")
allowlist.add_emr_cluster("j-ABC123DEF456")
```

**MVP Behavior:**
- If allowlist is empty → allows all (for development)
- If allowlist has entries → only allows listed resources
- Can be disabled with `ALLOWLIST_ENABLED=false`

## Local Development

### Using Docker Compose

```bash
# Start the server
docker-compose up data-execution-glue-emr

# Or in detached mode
docker-compose up -d data-execution-glue-emr
```

### Manual Docker Build

```bash
cd mcp-servers/data-execution-glue-emr
docker build -t mcp-data-execution-glue-emr .
docker run -p 8003:8003 \
  -e AWS_REGION=us-east-1 \
  -v ~/.aws:/root/.aws:ro \
  mcp-data-execution-glue-emr
```

### Direct Python Execution

```bash
cd mcp-servers/data-execution-glue-emr
pip install -e .
uvicorn data_execution.app:app --host 0.0.0.0 --port 8003
```

## Testing

### Health Check

```bash
curl http://localhost:8003/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "data-execution-glue-emr"
}
```

### Test Get Glue Job Run

```bash
curl -X POST http://localhost:8003/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_glue_job_run",
    "arguments": {
      "job_name": "my-glue-job",
      "run_id": "jr_abc123def456"
    }
  }'
```

### Test Get EMR Step

```bash
curl -X POST http://localhost:8003/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_emr_step",
    "arguments": {
      "cluster_id": "j-ABC123DEF456",
      "step_id": "s-ABC123DEF456"
    }
  }'
```

## AWS Deployment

### ECS Fargate

The server is designed to run on ECS Fargate:

1. **Build and push Docker image:**
   ```bash
   docker build -t data-execution-glue-emr .
   docker tag data-execution-glue-emr:latest <ECR_URI>/data-execution-glue-emr:latest
   docker push <ECR_URI>/data-execution-glue-emr:latest
   ```

2. **Terraform Configuration:**
   See `infra/terraform/main.tf` for ECS service definition.

3. **Environment Variables:**
   - Set via ECS task definition
   - IAM role provides AWS credentials automatically

### Service Discovery

In AWS, the server is accessible via:
- Service name: `mcp-data-execution-glue-emr`
- Port: `8003`
- Health check: `http://mcp-data-execution-glue-emr:8003/health`

## Use Cases

### Pipeline Failure Investigation

When a Step Functions execution fails and involves a Glue job:

```python
# Get Glue job run details
job_run = glue_client.get_job_run(
    job_name="my-glue-job",
    run_id="jr_abc123"
)

# Get associated log groups
log_groups = glue_client.get_log_groups_for_job("my-glue-job")

# Query logs using observability MCP server
# (log_groups can be passed to query_logs tool)
```

### EMR Step Analysis

When an EMR step fails:

```python
# Get step details
step = emr_client.get_step(
    cluster_id="j-ABC123DEF456",
    step_id="s-ABC123DEF456"
)

# Get cluster details
cluster = emr_client.get_cluster("j-ABC123DEF456")

# Get log groups for further investigation
log_groups = emr_client.get_log_groups_for_cluster("j-ABC123DEF456")
```

## Error Handling

The server returns structured error responses:

```json
{
  "detail": "Glue job not in allowlist: unauthorized-job"
}
```

Common error codes:
- `400`: Bad request (validation error)
- `403`: Forbidden (not in allowlist)
- `404`: Not found (job/cluster/step doesn't exist)
- `500`: Internal server error

## Logging

Structured logging format:
```
2024-01-15 10:00:00 - data_execution.app - INFO - Tool call: get_glue_job_run with arguments: {...}
2024-01-15 10:00:01 - data_execution.aws_glue - INFO - Retrieved job run jr_abc123 for job my-glue-job
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: `http://localhost:8003/docs`
- ReDoc: `http://localhost:8003/redoc`

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `boto3`: AWS SDK
- `pydantic`: Data validation
- `httpx`: HTTP client (for health checks)

## License

Part of the ops-autopilot project.
