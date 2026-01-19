# Orchestration MCP Server

MCP (Model Context Protocol) server for AWS Step Functions operations. Provides safe, typed, auditable tool APIs for interacting with Step Functions executions and state machines.

## Overview

The Orchestration MCP Server enables the Agent Host to:
- List and query Step Functions executions
- Get execution details and history
- Start and stop executions
- Support multi-region operations (auto-detects region from ARNs)

## Features

- ✅ **Multi-region Support**: Automatically detects AWS region from ARNs
- ✅ **Resource Allowlist**: Security boundary to restrict access to specific state machines/executions
- ✅ **Type-safe APIs**: Pydantic schemas for request/response validation
- ✅ **Structured Logging**: Consistent, auditable logging
- ✅ **Health Checks**: `/health` endpoint for monitoring
- ✅ **Error Handling**: Graceful error handling with detailed error messages

## Architecture

```
Agent Host
    ↓
MCP Client (HTTP)
    ↓
Orchestration MCP Server (FastAPI)
    ↓
AWS Step Functions (boto3)
```

## Tools

### 1. `list_executions`

List Step Functions executions for a state machine.

**Request:**
```json
{
  "tool": "list_executions",
  "arguments": {
    "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine",
    "status_filter": "FAILED",
    "max_results": 100,
    "next_token": null,
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "result": {
    "executions": [
      {
        "executionArn": "arn:aws:states:...",
        "stateMachineArn": "arn:aws:states:...",
        "name": "execution-123",
        "status": "FAILED",
        "startDate": "2024-01-15T10:00:00Z",
        "stopDate": "2024-01-15T10:05:00Z"
      }
    ],
    "nextToken": null
  }
}
```

### 2. `get_execution_details`

Get detailed information about a specific execution.

**Request:**
```json
{
  "tool": "get_execution_details",
  "arguments": {
    "execution_arn": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-123",
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "result": {
    "executionArn": "arn:aws:states:...",
    "stateMachineArn": "arn:aws:states:...",
    "name": "execution-123",
    "status": "FAILED",
    "startDate": "2024-01-15T10:00:00Z",
    "stopDate": "2024-01-15T10:05:00Z",
    "input": "{\"key\": \"value\"}",
    "output": null,
    "error": "States.TaskFailed",
    "cause": "Error message here"
  }
}
```

### 3. `get_execution_history`

Get execution history (events) for debugging and analysis.

**Request:**
```json
{
  "tool": "get_execution_history",
  "arguments": {
    "execution_arn": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-123",
    "max_results": 1000,
    "next_token": null,
    "reverse_order": false,
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "result": {
    "events": [
      {
        "id": 1,
        "type": "ExecutionStarted",
        "timestamp": "2024-01-15T10:00:00Z",
        "executionStartedEventDetails": {...}
      },
      {
        "id": 2,
        "type": "TaskStateEntered",
        "timestamp": "2024-01-15T10:00:05Z",
        "stateEnteredEventDetails": {...}
      }
    ],
    "nextToken": null
  }
}
```

### 4. `start_execution`

Start a new Step Functions execution.

**Request:**
```json
{
  "tool": "start_execution",
  "arguments": {
    "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine",
    "input_data": {"key": "value"},
    "name": "execution-123",
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "result": {
    "executionArn": "arn:aws:states:...",
    "startDate": "2024-01-15T10:00:00Z"
  }
}
```

### 5. `stop_execution`

Stop a running execution.

**Request:**
```json
{
  "tool": "stop_execution",
  "arguments": {
    "execution_arn": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-123",
    "error": "UserRequested",
    "cause": "Stopped by Agent Host",
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "result": {
    "stopDate": "2024-01-15T10:05:00Z"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8001` |
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

## Security

### Resource Allowlist

The server supports an allowlist to restrict access to specific state machines and executions:

```python
# In allowlist.py
allowlist.add_state_machine("arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine")
allowlist.add_execution("arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-123")
```

**MVP Behavior:**
- If allowlist is empty → allows all (for development)
- If allowlist has entries → only allows listed resources
- Can be disabled with `ALLOWLIST_ENABLED=false`

## Multi-Region Support

The server automatically detects AWS region from ARNs:

```python
# Region extracted from ARN
execution_arn = "arn:aws:states:us-west-2:123456789012:execution:MyStateMachine:exec-123"
# Automatically uses us-west-2 region

# Can also override explicitly
arguments = {
    "execution_arn": execution_arn,
    "region": "us-east-1"  # Override
}
```

The server maintains a client cache per region for optimal performance.

## Local Development

### Using Docker Compose

```bash
# Start the server
docker-compose up orchestration-sfn

# Or in detached mode
docker-compose up -d orchestration-sfn
```

### Manual Docker Build

```bash
cd mcp-servers/orchestration-sfn
docker build -t mcp-orchestration-sfn .
docker run -p 8001:8001 \
  -e AWS_REGION=us-east-1 \
  -v ~/.aws:/root/.aws:ro \
  mcp-orchestration-sfn
```

### Direct Python Execution

```bash
cd mcp-servers/orchestration-sfn
pip install -e .
uvicorn orchestration_sfn.app:app --host 0.0.0.0 --port 8001
```

## Testing

### Health Check

```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "orchestration-sfn"
}
```

### Test Tool Call

```bash
curl -X POST http://localhost:8001/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_executions",
    "arguments": {
      "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine",
      "max_results": 10
    }
  }'
```

## AWS Deployment

### ECS Fargate

The server is designed to run on ECS Fargate:

1. **Build and push Docker image:**
   ```bash
   docker build -t orchestration-sfn .
   docker tag orchestration-sfn:latest <ECR_URI>/orchestration-sfn:latest
   docker push <ECR_URI>/orchestration-sfn:latest
   ```

2. **Terraform Configuration:**
   See `infra/terraform/main.tf` for ECS service definition.

3. **Environment Variables:**
   - Set via ECS task definition
   - IAM role provides AWS credentials automatically

### Service Discovery

In AWS, the server is accessible via:
- Service name: `mcp-orchestration-sfn`
- Port: `8001`
- Health check: `http://mcp-orchestration-sfn:8001/health`

## Error Handling

The server returns structured error responses:

```json
{
  "detail": "State machine not in allowlist: arn:aws:states:..."
}
```

Common error codes:
- `400`: Bad request (validation error)
- `403`: Forbidden (not in allowlist)
- `500`: Internal server error

## Logging

Structured logging format:
```
2024-01-15 10:00:00 - orchestration_sfn.app - INFO - Tool call: list_executions with arguments: {...}
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `boto3`: AWS SDK
- `pydantic`: Data validation
- `httpx`: HTTP client (for health checks)

## License

Part of the ops-autopilot project.
