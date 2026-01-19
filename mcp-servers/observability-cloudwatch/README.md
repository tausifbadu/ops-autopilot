# Observability CloudWatch MCP Server

MCP (Model Context Protocol) server for AWS CloudWatch Logs and Metrics operations. Provides safe, typed, auditable tool APIs for querying logs, extracting error patterns, and retrieving metrics.

## Overview

The Observability CloudWatch MCP Server enables the Agent Host to:
- Query CloudWatch Logs using Logs Insights
- Get log events from log groups/streams
- Extract error fingerprints from logs
- Retrieve CloudWatch Metrics statistics
- List available metrics

## Features

- ✅ **CloudWatch Logs Insights**: Query logs with powerful query language
- ✅ **Log Event Retrieval**: Get filtered log events
- ✅ **Error Fingerprint Extraction**: Automatically extract error patterns
- ✅ **CloudWatch Metrics**: Get metric statistics and list metrics
- ✅ **Log Group Allowlist**: Security boundary to restrict access
- ✅ **Type-safe APIs**: Pydantic schemas for request/response validation
- ✅ **Structured Logging**: Consistent, auditable logging
- ✅ **Health Checks**: `/health` endpoint for monitoring

## Architecture

```
Agent Host
    ↓
MCP Client (HTTP)
    ↓
Observability CloudWatch MCP Server (FastAPI)
    ↓
AWS CloudWatch Logs & Metrics (boto3)
```

## Tools

### 1. `query_logs`

Query CloudWatch Logs using Logs Insights query language.

**Request:**
```json
{
  "tool": "query_logs",
  "arguments": {
    "log_groups": ["/aws/lambda/my-function", "/aws/glue/jobs/my-job"],
    "query": "fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 100",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "limit": 1000
  }
}
```

**Response:**
```json
{
  "result": {
    "query_id": "abc123...",
    "status": "Complete",
    "statistics": {
      "recordsScanned": 5000,
      "recordsMatched": 150
    },
    "results": [
      {
        "@timestamp": "2024-01-15T10:30:00.000Z",
        "@message": "ERROR: Connection timeout",
        "@logStream": "stream-123"
      }
    ]
  }
}
```

**Query Examples:**
```sql
# Find all errors
fields @timestamp, @message | filter @message like /ERROR/

# Count errors by type
fields @message | filter @message like /ERROR/ | stats count() by @message

# Get recent exceptions
fields @timestamp, @message | filter @message like /Exception/ | sort @timestamp desc | limit 50
```

### 2. `get_log_events`

Get log events from a log group or specific log stream.

**Request:**
```json
{
  "tool": "get_log_events",
  "arguments": {
    "log_group": "/aws/lambda/my-function",
    "log_stream": "2024/01/15/[$LATEST]abc123",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "limit": 100,
    "filter_pattern": "ERROR"
  }
}
```

**Response:**
```json
{
  "result": {
    "log_group": "/aws/lambda/my-function",
    "events": [
      {
        "eventId": "1234567890",
        "timestamp": 1705312800000,
        "message": "ERROR: Connection timeout",
        "ingestionTime": 1705312801000
      }
    ],
    "next_token": "abc123..."
  }
}
```

### 3. `extract_error_fingerprints`

Extract error fingerprints (exception names, error patterns) from log events.

**Request:**
```json
{
  "tool": "extract_error_fingerprints",
  "arguments": {
    "log_events": [
      {
        "message": "ValueError: Invalid input data",
        "timestamp": 1705312800000
      },
      {
        "message": "Connection timeout occurred",
        "timestamp": 1705312801000
      }
    ]
  }
}
```

**Response:**
```json
{
  "result": {
    "fingerprints": [
      "ValueError",
      "TIMEOUT"
    ]
  }
}
```

**Extracted Patterns:**
- Exception class names (e.g., `ValueError`, `TimeoutException`)
- Common error keywords: `TIMEOUT`, `PERMISSION_DENIED`, `CONNECTION_REFUSED`, `OUT_OF_MEMORY`

### 4. `get_metrics`

Get CloudWatch metric statistics.

**Request:**
```json
{
  "tool": "get_metrics",
  "arguments": {
    "namespace": "AWS/ECS",
    "metric_name": "CPUUtilization",
    "dimensions": [
      {
        "Name": "ServiceName",
        "Value": "my-service"
      },
      {
        "Name": "ClusterName",
        "Value": "my-cluster"
      }
    ],
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "period": 300,
    "statistics": ["Average", "Maximum", "Minimum"],
    "unit": "Percent"
  }
}
```

**Response:**
```json
{
  "result": {
    "namespace": "AWS/ECS",
    "metric_name": "CPUUtilization",
    "label": "CPUUtilization",
    "datapoints": [
      {
        "Timestamp": "2024-01-15T10:05:00Z",
        "Average": 45.5,
        "Maximum": 78.2,
        "Minimum": 12.3,
        "Unit": "Percent"
      }
    ]
  }
}
```

### 5. `list_metrics`

List available CloudWatch metrics.

**Request:**
```json
{
  "tool": "list_metrics",
  "arguments": {
    "namespace": "AWS/ECS",
    "metric_name": "CPUUtilization",
    "dimensions": [
      {
        "Name": "ServiceName",
        "Value": "my-service"
      }
    ]
  }
}
```

**Response:**
```json
{
  "result": {
    "metrics": [
      {
        "Namespace": "AWS/ECS",
        "MetricName": "CPUUtilization",
        "Dimensions": [
          {
            "Name": "ServiceName",
            "Value": "my-service"
          }
        ]
      }
    ]
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8002` |
| `AWS_REGION` | Default AWS region | `us-east-1` |
| `AWS_ENDPOINT_URL` | AWS endpoint URL (for local testing) | `None` |
| `ALLOWLIST_ENABLED` | Enable log group allowlist | `true` |
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
        "logs:StartQuery",
        "logs:GetQueryResults",
        "logs:FilterLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security

### Log Group Allowlist

The server supports an allowlist to restrict access to specific log groups:

```python
# In allowlist.py
allowlist.add_log_group("/aws/lambda/my-function")
allowlist.add_log_group("/aws/glue/jobs/my-job")
```

**MVP Behavior:**
- If allowlist is empty → allows all (for development)
- If allowlist has entries → only allows listed log groups
- Can be disabled with `ALLOWLIST_ENABLED=false`

## Local Development

### Using Docker Compose

```bash
# Start the server
docker-compose up observability-cloudwatch

# Or in detached mode
docker-compose up -d observability-cloudwatch
```

### Manual Docker Build

```bash
cd mcp-servers/observability-cloudwatch
docker build -t mcp-observability-cloudwatch .
docker run -p 8002:8002 \
  -e AWS_REGION=us-east-1 \
  -v ~/.aws:/root/.aws:ro \
  mcp-observability-cloudwatch
```

### Direct Python Execution

```bash
cd mcp-servers/observability-cloudwatch
pip install -e .
uvicorn observability_cloudwatch.app:app --host 0.0.0.0 --port 8002
```

## Testing

### Health Check

```bash
curl http://localhost:8002/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "observability-cloudwatch"
}
```

### Test Query Logs

```bash
curl -X POST http://localhost:8002/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "query_logs",
    "arguments": {
      "log_groups": ["/aws/lambda/my-function"],
      "query": "fields @timestamp, @message | filter @message like /ERROR/ | limit 10",
      "start_time": "2024-01-15T10:00:00Z",
      "end_time": "2024-01-15T11:00:00Z"
    }
  }'
```

### Test Get Metrics

```bash
curl -X POST http://localhost:8002/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_metrics",
    "arguments": {
      "namespace": "AWS/ECS",
      "metric_name": "CPUUtilization",
      "start_time": "2024-01-15T10:00:00Z",
      "end_time": "2024-01-15T11:00:00Z",
      "period": 300
    }
  }'
```

## AWS Deployment

### ECS Fargate

The server is designed to run on ECS Fargate:

1. **Build and push Docker image:**
   ```bash
   docker build -t observability-cloudwatch .
   docker tag observability-cloudwatch:latest <ECR_URI>/observability-cloudwatch:latest
   docker push <ECR_URI>/observability-cloudwatch:latest
   ```

2. **Terraform Configuration:**
   See `infra/terraform/main.tf` for ECS service definition.

3. **Environment Variables:**
   - Set via ECS task definition
   - IAM role provides AWS credentials automatically

### Service Discovery

In AWS, the server is accessible via:
- Service name: `mcp-observability-cloudwatch`
- Port: `8002`
- Health check: `http://mcp-observability-cloudwatch:8002/health`

## CloudWatch Logs Insights Query Language

The server uses CloudWatch Logs Insights query language. Common patterns:

### Find Errors
```sql
fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc
```

### Count by Pattern
```sql
fields @message | filter @message like /timeout/ | stats count() by @message
```

### Extract Fields
```sql
fields @timestamp, @message, @logStream | parse @message "ERROR: *" as error_msg
```

### Time Range Filtering
```sql
fields @timestamp, @message | filter @timestamp > 1705312800000 | sort @timestamp desc
```

## Error Handling

The server returns structured error responses:

```json
{
  "detail": "Log group not in allowlist: /aws/lambda/unauthorized"
}
```

Common error codes:
- `400`: Bad request (validation error)
- `403`: Forbidden (not in allowlist)
- `500`: Internal server error

## Logging

Structured logging format:
```
2024-01-15 10:00:00 - observability_cloudwatch.app - INFO - Tool call: query_logs with arguments: {...}
2024-01-15 10:00:01 - observability_cloudwatch.aws_logs - INFO - Started query abc123 for 2 log groups
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: `http://localhost:8002/docs`
- ReDoc: `http://localhost:8002/redoc`

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `boto3`: AWS SDK
- `pydantic`: Data validation
- `httpx`: HTTP client (for health checks)

## License

Part of the ops-autopilot project.
