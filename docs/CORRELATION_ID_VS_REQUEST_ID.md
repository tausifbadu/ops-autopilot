# Correlation ID vs Request ID: Relationship and Usage

**Purpose**: Clarify the relationship between `correlation_id` and `request_id` in Ops AutoPilot's distributed system.

---

## Quick Summary

| ID Type | Scope | Lifetime | Purpose |
|---------|-------|----------|---------|
| **`correlation_id`** | Entire incident/job | From event ingestion to completion | Groups all related operations for one business transaction |
| **`request_id`** | Single HTTP request/tool call | One request-response cycle | Uniquely identifies a specific API call |

**Relationship**: One `correlation_id` contains many `request_id`s (1:N relationship)

---

## Detailed Explanation

### Correlation ID (`correlation_id`)

**Definition**: A unique identifier that **correlates all operations** related to a single business transaction (incident/job).

**Characteristics**:
- **Generated once** at the start of an incident/job
- **Propagated** through all downstream operations
- **Persists** for the entire lifecycle of the incident
- **Groups** all related logs, tool calls, and actions together

**Use Cases**:
- Trace an incident from event → investigation → remediation → verification
- Correlate logs across Agent Host, MCP servers, and AWS services
- Debug distributed failures by following one correlation ID
- Generate audit trails for compliance

**Example Flow**:
```
Event arrives → correlation_id: "corr_abc123"
  ↓
Coordinator processes → Uses correlation_id: "corr_abc123"
  ↓
Pipeline RCA Agent investigates → Uses correlation_id: "corr_abc123"
  ↓
MCP Client calls orchestration-sfn → Uses correlation_id: "corr_abc123"
  ↓
MCP Client calls observability-cloudwatch → Uses correlation_id: "corr_abc123"
  ↓
Remediation Agent executes → Uses correlation_id: "corr_abc123"
  ↓
All logs/audit records share: correlation_id: "corr_abc123"
```

**In Code**:
```python
# Generated once at job start
correlation_id = f"corr_{uuid4().hex[:16]}"  # e.g., "corr_abc123def456"

# Propagated through all operations
job_envelope = JobEnvelope(
    correlation_id=correlation_id,  # Same ID for entire job
    incident_id=incident_id,
    # ...
)
```

---

### Request ID (`request_id`)

**Definition**: A unique identifier for a **single HTTP request** or **tool call**.

**Characteristics**:
- **Generated per request** (each tool call gets a new one)
- **Scoped to one request-response cycle**
- **Used for** request-level tracing and debugging
- **Helps identify** specific API calls in logs

**Use Cases**:
- Debug a specific tool call failure
- Track request latency for a single API call
- Identify retries (same request_id on retry, or new request_id?)
- Correlate request/response pairs in logs

**Example Flow**:
```
MCP Client calls orchestration-sfn.describe_execution
  → request_id: "req_xyz789"
  → correlation_id: "corr_abc123" (inherited from job)

MCP Client calls observability-cloudwatch.query_logs
  → request_id: "req_abc456" (NEW - different request)
  → correlation_id: "corr_abc123" (SAME - same job)

MCP Client calls orchestration-sfn.start_execution
  → request_id: "req_def012" (NEW - different request)
  → correlation_id: "corr_abc123" (SAME - same job)
```

**In Code**:
```python
# Generated per tool call
def call_tool(self, tool_name: str, arguments: dict, correlation_id: str):
    request_id = f"req_{uuid4().hex[:16]}"  # NEW ID per call
    
    # Both IDs in headers
    headers = {
        "X-Correlation-ID": correlation_id,  # Same for all calls in job
        "X-Request-ID": request_id            # Unique per call
    }
    
    # Log with both
    self.audit_logger.log_tool_call(
        correlation_id=correlation_id,  # Groups all calls
        request_id=request_id,           # Identifies this call
        # ...
    )
```

---

## Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Incident/Job: correlation_id = "corr_abc123"                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Tool Call 1: orchestration-sfn.describe_execution            │
│    ├─ request_id: "req_xyz789"                               │
│    └─ correlation_id: "corr_abc123" ← Same                   │
│                                                               │
│  Tool Call 2: observability-cloudwatch.query_logs            │
│    ├─ request_id: "req_abc456" ← Different                  │
│    └─ correlation_id: "corr_abc123" ← Same                   │
│                                                               │
│  Tool Call 3: orchestration-sfn.start_execution              │
│    ├─ request_id: "req_def012" ← Different                  │
│    └─ correlation_id: "corr_abc123" ← Same                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Point**: All three tool calls share the same `correlation_id` but have different `request_id`s.

---

## When to Use Each

### Use `correlation_id` when:
- ✅ **Tracing an entire incident** from start to finish
- ✅ **Grouping related operations** (all tool calls for one incident)
- ✅ **Debugging distributed failures** (find all logs for one incident)
- ✅ **Generating audit trails** (compliance reporting)
- ✅ **Correlating logs** across multiple services
- ✅ **Querying**: "Show me everything that happened for incident X"

**Example Query**:
```python
# Find all operations for one incident
audit_records = audit_store.query_by_correlation_id("corr_abc123")
# Returns: All tool calls, actions, and logs for this incident
```

### Use `request_id` when:
- ✅ **Debugging a specific API call** failure
- ✅ **Tracking request latency** for one tool call
- ✅ **Identifying retries** (same request_id = retry, new request_id = new call)
- ✅ **Correlating request/response** pairs in logs
- ✅ **Querying**: "What happened with this specific tool call?"

**Example Query**:
```python
# Find details of one specific tool call
audit_record = audit_store.query_by_request_id("req_xyz789")
# Returns: Details of that specific orchestration-sfn.describe_execution call
```

---

## Implementation in Ops AutoPilot

### 1. Job Envelope (Entry Point)

```python
# shared/src/shared/schemas/job_envelope.py
class JobEnvelope(BaseModel):
    """Standardized job envelope per skill.md."""
    correlation_id: str = Field(
        default_factory=lambda: f"corr_{uuid4().hex[:16]}",
        description="Correlates all operations for this job"
    )
    incident_id: Optional[str] = None
    # ... other fields
```

**Generated**: Once when event is normalized into JobEnvelope  
**Propagated**: Through all workflows, agents, and tool calls

---

### 2. MCP Client (Tool Calls)

```python
# agent-host/src/agent_host/mcp_client/base.py
class MCPClient:
    def call_tool(
        self, 
        tool_name: str, 
        arguments: dict, 
        correlation_id: str  # Inherited from job
    ) -> ToolResult:
        # Generate NEW request_id per call
        request_id = f"req_{uuid4().hex[:16]}"
        
        # Propagate both IDs
        headers = {
            "X-Correlation-ID": correlation_id,  # From job
            "X-Request-ID": request_id             # New per call
        }
        
        # Make HTTP request
        response = self.http_client.post(
            f"{self.base_url}/tools",
            json={"tool": tool_name, "arguments": arguments},
            headers=headers
        )
        
        # Log audit record with both IDs
        self.audit_logger.log_tool_call(
            correlation_id=correlation_id,
            request_id=request_id,
            tool_name=tool_name,
            latency=elapsed_time,
            status=response.status_code,
            # ...
        )
        
        return ToolResult(
            correlation_id=correlation_id,
            request_id=request_id,
            result=response.json()
        )
```

---

### 3. MCP Server (Receives IDs)

```python
# mcp-servers/orchestration-sfn/app.py
@app.post("/tools")
def call_tool(request: ToolRequest):
    # Extract IDs from headers
    correlation_id = request.headers.get("X-Correlation-ID")
    request_id = request.headers.get("X-Request-ID")
    
    # Log with both IDs
    logger.info(
        f"Tool call: {request.tool}",
        extra={
            "correlation_id": correlation_id,
            "request_id": request_id,
            "tool": request.tool
        }
    )
    
    # Make AWS API call
    result = aws_client.describe_execution(...)
    
    # Return with both IDs
    return {
        "result": result,
        "correlation_id": correlation_id,
        "request_id": request_id
    }
```

---

### 4. Audit Logging

```python
# agent-host/src/agent_host/audit/logger.py
class AuditLogger:
    def log_tool_call(
        self,
        correlation_id: str,  # Groups all calls for one incident
        request_id: str,        # Identifies this specific call
        incident_id: str,
        tool_name: str,
        latency: timedelta,
        status: str,
        # ...
    ):
        audit_record = {
            "correlation_id": correlation_id,  # Index for grouping
            "request_id": request_id,           # Index for specific lookup
            "incident_id": incident_id,
            "tool_name": tool_name,
            "latency_ms": latency.total_seconds() * 1000,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in DynamoDB with both as indexes
        self.audit_store.save(audit_record)
```

---

## Query Patterns

### Find All Operations for One Incident

```python
# Query by correlation_id (groups everything)
audit_records = audit_store.query(
    index="correlation_id-index",
    key="corr_abc123"
)
# Returns: All tool calls, actions, logs for this incident
```

### Find Specific Tool Call

```python
# Query by request_id (specific call)
audit_record = audit_store.query(
    index="request_id-index",
    key="req_xyz789"
)
# Returns: Details of that specific tool call
```

### Find All Failed Tool Calls for One Incident

```python
# Query by correlation_id + filter by status
audit_records = audit_store.query(
    index="correlation_id-index",
    key="corr_abc123",
    filter_expression="status = :failed",
    expression_values={":failed": "failed"}
)
# Returns: All failed tool calls for this incident
```

---

## Comparison with Other IDs

| ID | Scope | Lifetime | Example |
|----|-------|----------|---------|
| **`correlation_id`** | Entire job | Job lifecycle | `corr_abc123` |
| **`request_id`** | Single request | Request-response | `req_xyz789` |
| **`incident_id`** | Business incident | Incident lifecycle | `incident_run-123_20240115` |
| **`execution_arn`** | AWS execution | Execution lifecycle | `arn:aws:states:...` |

**Relationship**:
```
incident_id: "incident_run-123_20240115"
  └─ correlation_id: "corr_abc123" (one per incident)
      ├─ request_id: "req_xyz789" (tool call 1)
      ├─ request_id: "req_abc456" (tool call 2)
      └─ request_id: "req_def012" (tool call 3)
```

---

## Best Practices

### ✅ DO

1. **Generate `correlation_id` once** at job start and propagate it everywhere
2. **Generate `request_id` per tool call** (new ID for each HTTP request)
3. **Include both IDs** in all logs and audit records
4. **Use `correlation_id`** for grouping related operations
5. **Use `request_id`** for debugging specific API calls
6. **Propagate both IDs** in HTTP headers (`X-Correlation-ID`, `X-Request-ID`)

### ❌ DON'T

1. **Don't reuse `request_id`** across different tool calls
2. **Don't generate new `correlation_id`** for each tool call
3. **Don't use `request_id`** to group operations (use `correlation_id`)
4. **Don't lose `correlation_id`** when making nested calls
5. **Don't use `incident_id`** as `correlation_id` (they serve different purposes)

---

## Example: Complete Flow

```python
# 1. Event arrives
event = {"type": "PIPELINE_FAILURE", "execution_arn": "..."}

# 2. Normalize to JobEnvelope (generate correlation_id)
job = JobEnvelope(
    type="PIPELINE_FAILURE",
    correlation_id="corr_abc123",  # Generated once
    incident_id="incident_run-123_20240115",
    # ...
)

# 3. Coordinator processes
coordinator.coordinate(job)
# Uses: correlation_id="corr_abc123"

# 4. Pipeline RCA Agent investigates
rca_agent.investigate(job)
# Uses: correlation_id="corr_abc123"

# 5. Tool Call 1: Get execution details
mcp_client.call_tool(
    "orchestration-sfn.describe_execution",
    {"execution_arn": "..."},
    correlation_id="corr_abc123"  # Inherited
)
# Generates: request_id="req_xyz789"
# Headers: X-Correlation-ID: corr_abc123, X-Request-ID: req_xyz789

# 6. Tool Call 2: Query logs
mcp_client.call_tool(
    "observability-cloudwatch.query_logs",
    {"log_group": "...", "time_range": "..."},
    correlation_id="corr_abc123"  # Same correlation_id
)
# Generates: request_id="req_abc456"  # NEW request_id
# Headers: X-Correlation-ID: corr_abc123, X-Request-ID: req_abc456

# 7. Audit Records
audit_store.query_by_correlation_id("corr_abc123")
# Returns:
# - request_id: req_xyz789, tool: describe_execution, status: success
# - request_id: req_abc456, tool: query_logs, status: success
# Both share: correlation_id: corr_abc123
```

---

## Summary

- **`correlation_id`**: Groups all operations for one incident/job (1 per job)
- **`request_id`**: Identifies a specific tool call/request (1 per call)
- **Relationship**: One `correlation_id` contains many `request_id`s (1:N)
- **Use `correlation_id`**: To trace entire incidents and group related operations
- **Use `request_id`**: To debug specific API calls and track request latency

Both IDs are essential for distributed tracing, debugging, and audit compliance.

---

**Last Updated**: Current Session  
**Related Documents**: 
- [PHASE0_GAP_ANALYSIS.md](PHASE0_GAP_ANALYSIS.md) - Gap #2: Correlation ID & Request ID Propagation
- [CODE_FLOW.md](CODE_FLOW.md) - Complete code flow documentation
