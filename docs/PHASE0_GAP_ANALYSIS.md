# Phase 0 Gap Analysis: skill.md Requirements

**Date**: Current Session  
**Phase**: Phase 0 MVP (~90% Complete)  
**Purpose**: Identify gaps between current Phase 0 implementation and skill.md principal engineer requirements  
**Status**: Critical gaps identified - Action required before Phase 0 completion

---

## Executive Summary

Phase 0 has solid foundations (Agent Host, MCP servers, policy engine, multi-region), but **15 critical gaps** must be addressed to meet skill.md's scalability, safety, and observability requirements. These gaps fall into 5 categories:

1. **Idempotency & Safety** (Critical - Blocks Production)
2. **Observability & Tracing** (Critical - Blocks Production)
3. **Rate Limiting & Throttling** (High - Blocks Scale)
4. **Job Envelope & Standardization** (High - Blocks Multi-Service)
5. **Platform Metrics & SLOs** (Medium - Blocks Operations)

**Recommendation**: Address Critical and High priority gaps before declaring Phase 0 complete.

---

## Gap Categories

### 🔴 Critical Priority (Blocks Production)

#### 1. Action-Level Idempotency

**skill.md Requirement** (Line 106-112):
> - job-level idempotency key
> - action-level idempotency key
> - store action results keyed by `(incident_id, action_type, target)`
> - For write actions, require: pre-check → execute → verify → record

**Current State**:
- ✅ Job-level idempotency exists (`incident_id` check in coordinator)
- ❌ **Missing**: Action-level idempotency keys
- ❌ **Missing**: Action results stored by `(incident_id, action_type, target)`
- ❌ **Missing**: Pre-check before write actions

**Impact**: Duplicate SQS messages could cause repeated remediation actions (e.g., rerun pipeline twice).

**Required Changes**:
```python
# agent-host/src/agent_host/agents/remediation_agent.py
class RemediationAgent:
    def execute_remediation(self, plan: RemediationPlan) -> RemediationResult:
        for action in plan.actions:
            # ADD: Generate action-level idempotency key
            action_key = f"{incident_id}:{action.action_type}:{action.target}"
            
            # ADD: Pre-check if action already executed
            if self.action_store.exists(action_key):
                logger.info(f"Action already executed: {action_key}")
                continue
            
            # ADD: Pre-check (verify current state before write)
            current_state = self._pre_check_action(action)
            if current_state == "already_desired":
                logger.info(f"Action target already in desired state: {action_key}")
                continue
            
            # Execute action...
            
            # ADD: Store action result
            self.action_store.save(action_key, {
                "incident_id": incident_id,
                "action_type": action.action_type,
                "target": action.target,
                "result": execution_result,
                "timestamp": datetime.utcnow()
            })
```

**New Component Needed**:
- `agent-host/src/agent_host/state/action_store.py` - DynamoDB table for action results

---

#### 2. Correlation ID & Request ID Propagation

**skill.md Requirement** (Line 234-238):
> Every tool call and action must be logged with:
> - request_id, correlation_id, incident_id
> - actor (agent), tool name/version, parameters (redacted if needed)
> - latency, status, error codes
> - Persist audit records for compliance and postmortems.

**Current State**:
- ✅ `incident_id` exists
- ❌ **Missing**: `correlation_id` generation and propagation
- ❌ **Missing**: `request_id` per tool call
- ❌ **Missing**: Tool version in audit logs
- ❌ **Missing**: Audit record persistence (separate from evidence)

**Impact**: Cannot trace incidents across systems, debug distributed failures, or meet compliance requirements.

**📖 See [CORRELATION_ID_VS_REQUEST_ID.md](CORRELATION_ID_VS_REQUEST_ID.md) for detailed explanation of the relationship between correlation_id and request_id.**

##### Understanding the Three IDs

**Key Differences**:

| ID | Scope | Lifetime | Purpose | Example |
|----|-------|----------|---------|---------|
| **`incident_id`** | Business incident | Incident lifecycle | Identifies a business incident | `incident_run-123_20240115` |
| **`correlation_id`** | Technical job/transaction | Job processing lifecycle | Groups all technical operations | `corr_abc123def456` |
| **`request_id`** | Single HTTP request | One request-response | Identifies a specific API call | `req_xyz789` |

**Relationship Hierarchy**:
```
incident_id (1 business incident)
  └─ correlation_id (1 per incident - groups all operations)
      └─ request_id (N per correlation_id - one per tool call)
```

**When to Use Each**:
- **`incident_id`**: Business reporting, tickets, notifications, long-term tracking
- **`correlation_id`**: Distributed tracing, debugging, audit trails, grouping operations
- **`request_id`**: Debugging specific API calls, tracking request latency, identifying retries

**Example Flow**:
```python
# 1. Business level - incident_id
incident_id = "incident_run-123456_20240115103000"

# 2. Technical level - correlation_id (generated once at job start)
correlation_id = "corr_abc123def456"

# 3. Request level - request_id (generated per tool call)
# Tool Call 1
request_id_1 = "req_xyz789"  # New ID per call
# Tool Call 2  
request_id_2 = "req_abc456"  # New ID per call
# Tool Call 3
request_id_3 = "req_def012"  # New ID per call

# All three tool calls share same correlation_id but have different request_ids
```

**Required Changes**:
```python
# shared/src/shared/schemas/common.py
class JobEnvelope(BaseModel):
    """Standardized job envelope per skill.md."""
    type: str
    time: datetime
    severity: str
    env: str  # prod, nonprod, dev
    region: str
    account_id: str
    resource_refs: list[str]
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid4().hex[:16]}")
    incident_id: Optional[str] = None

# agent-host/src/agent_host/mcp_client/base.py
class MCPClient:
    def call_tool(self, tool_name: str, arguments: dict, correlation_id: str) -> ToolResult:
        request_id = f"req_{uuid4().hex[:16]}"
        
        # Propagate correlation_id and request_id
        headers = {
            "X-Correlation-ID": correlation_id,
            "X-Request-ID": request_id
        }
        
        # Log audit record
        self.audit_logger.log_tool_call(
            correlation_id=correlation_id,
            request_id=request_id,
            incident_id=self.current_incident_id,
            actor=self.actor_name,
            tool_name=tool_name,
            tool_version=self._get_tool_version(tool_name),  # NEW
            parameters=self._redact_secrets(arguments),
            latency=elapsed_time,
            status=result.status,
            error_code=result.error_code if result.error else None
        )
```

**New Component Needed**:
- `agent-host/src/agent_host/audit/logger.py` - Audit logging with DynamoDB persistence
- `agent-host/src/agent_host/audit/store.py` - Audit record storage (DynamoDB table)

---

#### 3. Tool Version Contracts & Registry

**skill.md Requirement** (Line 57-61, 130-134):
> - Every tool has a semantic version: `sfn.describe_execution@v1`
> - Agent workflows pin tool versions
> - MCP servers support N-1 versions and provide deprecation warnings
> - Register tool in Tool Registry with metadata:
>   - tool name/version
>   - auth scope needed
>   - cost/latency class (LOW/MED/HIGH)

**Current State**:
- ❌ **Missing**: Tool versioning in MCP protocol
- ❌ **Missing**: Tool Registry metadata store
- ❌ **Missing**: Workflow tool version pinning
- ❌ **Missing**: Cost/latency class metadata

**Impact**: Cannot safely upgrade tools, track costs, or enforce budgets.

**Required Changes**:
```python
# mcp-servers/orchestration-sfn/app.py
@app.get("/tools")
def list_tools():
    return {
        "tools": [
            {
                "name": "describe_execution",
                "version": "v1",
                "cost_class": "LOW",
                "latency_class": "LOW",
                "auth_scope": "states:DescribeExecution"
            },
            # ...
        ]
    }

# agent-host/src/agent_host/workflows/pipeline_failure.py
class PipelineFailureWorkflow:
    # Pin tool versions
    REQUIRED_TOOLS = {
        "orchestration-sfn.describe_execution": "v1",
        "observability-cloudwatch.query_logs": "v1",
        # ...
    }
    
    def _validate_tool_versions(self):
        for tool_name, required_version in self.REQUIRED_TOOLS.items():
            available_version = self.mcp_client.get_tool_version(tool_name)
            if available_version != required_version:
                raise ToolVersionMismatchError(...)
```

**New Component Needed**:
- `agent-host/src/agent_host/registry/tool_registry.py` - Tool metadata store
- Tool versioning in MCP protocol spec

---

#### 4. Circuit Breakers & Safety Degradation

**skill.md Requirement** (Line 229-231):
> - circuit breakers:
>   - disable auto-actions on repeated failures
>   - degrade to notify-only mode when confidence is low

**Current State**:
- ✅ Policy engine has rate limiting
- ❌ **Missing**: Circuit breaker state tracking
- ❌ **Missing**: Automatic degradation to notify-only mode
- ❌ **Missing**: Per-workflow circuit breaker state

**Impact**: System could repeatedly attempt failed remediations, wasting resources and causing cascading failures.

**Required Changes**:
```python
# agent-host/src/agent_host/policy/circuit_breaker.py
class CircuitBreaker:
    def __init__(self):
        self.failure_counts: dict[str, int] = {}  # workflow_id -> count
        self.open_circuits: set[str] = set()  # workflow_ids with open circuits
    
    def record_failure(self, workflow_id: str):
        self.failure_counts[workflow_id] = self.failure_counts.get(workflow_id, 0) + 1
        if self.failure_counts[workflow_id] >= 3:  # Threshold
            self.open_circuits.add(workflow_id)
            logger.warning(f"Circuit breaker opened for workflow: {workflow_id}")
    
    def is_open(self, workflow_id: str) -> bool:
        return workflow_id in self.open_circuits
    
    def should_degrade(self, confidence: float) -> bool:
        return confidence < 0.7  # Degrade if confidence low

# agent-host/src/agent_host/agents/coordinator.py
def coordinate(self, event) -> DecisionPacket:
    workflow_id = event.workflow_id
    
    # Check circuit breaker
    if self.circuit_breaker.is_open(workflow_id):
        logger.warning(f"Circuit breaker open for {workflow_id}, notify-only mode")
        return self._notify_only_decision(event)
    
    # Check confidence
    if investigation.confidence < 0.7:
        if self.circuit_breaker.should_degrade(confidence):
            logger.warning(f"Low confidence ({confidence}), notify-only mode")
            return self._notify_only_decision(event)
```

**New Component Needed**:
- `agent-host/src/agent_host/policy/circuit_breaker.py` - Circuit breaker state management

---

### 🟠 High Priority (Blocks Scale)

#### 5. AWS API Throttling & Rate Limiting

**skill.md Requirement** (Line 94-99):
> Design for AWS API throttling:
> - exponential backoff + jitter
> - adaptive concurrency limits per tool/service
> - token-bucket rate limiting per account/region
> - Separate "heavy" tasks (log queries, Athena scans) into bounded, budgeted subjobs.

**Current State**:
- ✅ MCP client has basic retry logic
- ❌ **Missing**: Exponential backoff with jitter
- ❌ **Missing**: Adaptive concurrency limits per tool
- ❌ **Missing**: Token-bucket rate limiting per account/region
- ❌ **Missing**: Heavy task isolation (log queries, Athena)

**Impact**: AWS API throttling will cause failures at scale. Heavy queries will block other operations.

**Required Changes**:
```python
# agent-host/src/agent_host/mcp_client/base.py
class MCPClient:
    def __init__(self):
        self.rate_limiter = TokenBucketRateLimiter(
            per_account_limits={"us-east-1": 100, "us-west-2": 100},
            per_service_limits={"cloudwatch": 50, "stepfunctions": 100}
        )
        self.concurrency_limiter = AdaptiveConcurrencyLimiter()
    
    def call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        # Check rate limits
        account_id = arguments.get("account_id")
        region = arguments.get("region")
        service = self._extract_service(tool_name)
        
        if not self.rate_limiter.acquire(account_id, region, service):
            raise RateLimitExceededError(...)
        
        # Check concurrency
        if not self.concurrency_limiter.acquire(tool_name):
            raise ConcurrencyLimitExceededError(...)
        
        try:
            # Exponential backoff with jitter
            return self._call_with_backoff(tool_name, arguments)
        finally:
            self.concurrency_limiter.release(tool_name)
    
    def _call_with_backoff(self, tool_name: str, arguments: dict, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                return self._http_call(tool_name, arguments)
            except ThrottlingException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential + jitter
                time.sleep(wait_time)
```

**New Component Needed**:
- `agent-host/src/agent_host/mcp_client/rate_limiter.py` - Token bucket rate limiter
- `agent-host/src/agent_host/mcp_client/concurrency_limiter.py` - Adaptive concurrency limiter

---

#### 6. Job Envelope Standardization

**skill.md Requirement** (Line 88-92):
> Standardize all inputs into a single `JobEnvelope`:
> - `type`, `time`, `severity`, `env`, `region`, `account_id`, `resource_refs`, `correlation_id`
> - Use EventBridge rules (per region) to route to SQS:
>   - `q-incidents` (high), `q-dq` (medium), `q-cost` (low), `q-batch` (scheduled)
> - Apply deduplication keys and idempotency at ingress.

**Current State**:
- ✅ Event schemas exist (`PipelineFailureEvent`, `APIFailureEvent`)
- ❌ **Missing**: Standardized `JobEnvelope` wrapper
- ❌ **Missing**: Multiple SQS queues (only incidents queue exists)
- ❌ **Missing**: Deduplication keys at ingress

**Impact**: Cannot route by priority, scale different workloads independently, or prevent duplicate processing.

**Required Changes**:
```python
# shared/src/shared/schemas/job_envelope.py
class JobEnvelope(BaseModel):
    """Standardized job envelope per skill.md."""
    type: str  # PIPELINE_FAILURE, DQ_CHECK, COST_SCAN, etc.
    time: datetime
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    env: str  # prod, nonprod, dev
    region: str
    account_id: str
    resource_refs: list[str]  # ARNs, resource IDs
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid4().hex[:16]}")
    incident_id: Optional[str] = None
    payload: dict  # Event-specific data

# agent-host/src/agent_host/dispatcher.py
class Dispatcher:
    QUEUE_MAPPING = {
        "PIPELINE_FAILURE": "q-incidents",
        "API_FAILURE": "q-incidents",
        "DQ_CHECK": "q-dq",
        "COST_SCAN": "q-cost",
        "DAILY_SWEEP": "q-batch"
    }
    
    def normalize_event(self, raw_event: dict) -> JobEnvelope:
        """Normalize any event into JobEnvelope."""
        return JobEnvelope(
            type=self._extract_type(raw_event),
            time=datetime.fromisoformat(raw_event["time"]),
            severity=self._extract_severity(raw_event),
            env=self._extract_env(raw_event),
            region=self._extract_region(raw_event),
            account_id=self._extract_account_id(raw_event),
            resource_refs=self._extract_resource_refs(raw_event),
            payload=raw_event
        )
    
    def route_to_queue(self, envelope: JobEnvelope) -> str:
        return self.QUEUE_MAPPING.get(envelope.type, "q-batch")
```

**Infrastructure Changes**:
- Terraform: Create multiple SQS queues (`q-incidents`, `q-dq`, `q-cost`, `q-batch`)
- EventBridge rules: Route to appropriate queue based on event type

---

#### 7. Heavy Task Isolation & Budgeting

**skill.md Requirement** (Line 99):
> Separate "heavy" tasks (log queries, Athena scans) into bounded, budgeted subjobs.

**Current State**:
- ✅ Coordinator has `max_tool_calls` budget
- ❌ **Missing**: Separate budgets for heavy tasks (CloudWatch queries, Athena)
- ❌ **Missing**: Heavy task isolation (async execution)
- ❌ **Missing**: Time window limits for queries

**Impact**: Long-running CloudWatch queries or Athena scans will block other operations and cause timeouts.

**Required Changes**:
```python
# agent-host/src/agent_host/agents/coordinator.py
class CoordinatorAgent:
    def __init__(self):
        self.heavy_task_budget = HeavyTaskBudget(
            max_cloudwatch_query_window=timedelta(minutes=30),
            max_athena_bytes_scanned=10_000_000_000,  # 10GB
            max_concurrent_heavy_tasks=2
        )
    
    def coordinate(self, event) -> DecisionPacket:
        # Check if task requires heavy operations
        if self._requires_heavy_tasks(event):
            if not self.heavy_task_budget.acquire():
                logger.warning("Heavy task budget exhausted, using lightweight mode")
                return self._lightweight_investigation(event)
            
            try:
                # Execute heavy tasks asynchronously
                heavy_results = await self._execute_heavy_tasks(event)
            finally:
                self.heavy_task_budget.release()
```

**New Component Needed**:
- `agent-host/src/agent_host/budget/heavy_task_budget.py` - Heavy task budget management

---

#### 8. Multi-Account Support (STS AssumeRole)

**skill.md Requirement** (Line 81):
> Support cross-account access using STS AssumeRole with scoped policies.

**Current State**:
- ✅ Multi-region support exists
- ❌ **Missing**: Multi-account support
- ❌ **Missing**: STS AssumeRole integration
- ❌ **Missing**: Per-account IAM role configuration

**Impact**: Cannot operate across multiple AWS accounts (common in enterprise setups).

**Required Changes**:
```python
# agent-host/src/agent_host/aws/sts_client.py
class STSClient:
    def assume_role(self, account_id: str, role_name: str, external_id: str = None):
        """Assume role in target account."""
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        sts = boto3.client('sts')
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"ops-autopilot-{uuid4().hex[:8]}",
            ExternalId=external_id
        )
        return response['Credentials']

# agent-host/src/agent_host/mcp_client/base.py
class MCPClient:
    def __init__(self):
        self.sts_client = STSClient()
        self.account_credentials: dict[str, dict] = {}  # account_id -> credentials
    
    def call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        account_id = arguments.get("account_id")
        if account_id and account_id != self.default_account_id:
            # Use cross-account credentials
            credentials = self._get_account_credentials(account_id)
            # Pass credentials to MCP server (or use regional role)
```

**New Component Needed**:
- `agent-host/src/agent_host/aws/sts_client.py` - STS AssumeRole client
- Configuration: Per-account role ARNs and external IDs

---

### 🟡 Medium Priority (Blocks Operations)

#### 9. Platform Metrics & SLOs

**skill.md Requirement** (Line 244-250):
> Metrics (platform SLOs):
> - job processing latency (p50/p95)
> - incident MTTA and MTTR changes
> - tool call success rate and throttling rate
> - auto-action success rate and rollback rate
> - false positive rate (post-human feedback)
> - platform cost (CW queries, Athena scans)

**Current State**:
- ❌ **Missing**: Platform metrics emission
- ❌ **Missing**: SLO tracking
- ❌ **Missing**: Cost tracking

**Impact**: Cannot measure platform health, identify bottlenecks, or track cost efficiency.

**Required Changes**:
```python
# agent-host/src/agent_host/metrics/platform_metrics.py
class PlatformMetrics:
    def record_job_processing(self, job_type: str, latency: timedelta, success: bool):
        self.cloudwatch.put_metric_data(
            Namespace="OpsAutoPilot/Platform",
            MetricData=[
                {
                    "MetricName": "JobProcessingLatency",
                    "Dimensions": [{"Name": "JobType", "Value": job_type}],
                    "Value": latency.total_seconds(),
                    "Unit": "Seconds",
                    "StatisticValues": {
                        "SampleCount": 1,
                        "Sum": latency.total_seconds(),
                        "Minimum": latency.total_seconds(),
                        "Maximum": latency.total_seconds()
                    }
                },
                {
                    "MetricName": "JobProcessingSuccess",
                    "Dimensions": [{"Name": "JobType", "Value": job_type}],
                    "Value": 1 if success else 0,
                    "Unit": "Count"
                }
            ]
        )
    
    def record_tool_call(self, tool_name: str, latency: timedelta, success: bool, throttled: bool):
        # Similar metrics for tool calls
        pass
    
    def record_auto_action(self, action_type: str, success: bool, rolled_back: bool):
        # Similar metrics for auto-actions
        pass
```

**New Component Needed**:
- `agent-host/src/agent_host/metrics/platform_metrics.py` - CloudWatch metrics emission
- CloudWatch dashboards for SLO monitoring

---

#### 10. Distributed Tracing

**skill.md Requirement** (Line 252-255):
> Tracing:
> - Correlate across: event → job → workflow → tool calls → actions
> - Propagate `correlation_id` and `X-Request-Id`.

**Current State**:
- ❌ **Missing**: Distributed tracing implementation
- ❌ **Missing**: Trace ID propagation
- ❌ **Missing**: Trace visualization

**Impact**: Cannot debug distributed failures or understand system behavior.

**Required Changes**:
```python
# agent-host/src/agent_host/tracing/tracer.py
class Tracer:
    def __init__(self):
        self.xray = boto3.client('xray')
    
    def start_trace(self, correlation_id: str) -> str:
        """Start a new trace segment."""
        segment_id = f"seg_{uuid4().hex[:16]}"
        self.xray.put_trace_segments(
            TraceSegmentDocuments=[
                json.dumps({
                    "trace_id": correlation_id,
                    "id": segment_id,
                    "start_time": time.time(),
                    "name": "OpsAutoPilot"
                })
            ]
        )
        return segment_id
    
    def add_subsegment(self, parent_id: str, name: str, metadata: dict):
        """Add subsegment to trace."""
        # X-Ray subsegment creation
        pass
```

**New Component Needed**:
- `agent-host/src/agent_host/tracing/tracer.py` - X-Ray tracing integration
- X-Ray service map configuration

---

#### 11. Verification Checklists

**skill.md Requirement** (Line 112):
> For write actions, require: pre-check → execute → verify → record

**Current State**:
- ✅ Verification exists in remediation agent (checks execution status)
- ❌ **Missing**: Standardized verification checklist
- ❌ **Missing**: Verification evidence storage
- ❌ **Missing**: Verification failure handling

**Impact**: Cannot prove remediation succeeded or failed, leading to uncertainty.

**Required Changes**:
```python
# agent-host/src/agent_host/agents/remediation_agent.py
class RemediationAgent:
    VERIFICATION_CHECKLISTS = {
        "start_execution": [
            "execution_state_changed_to_running",
            "execution_arn_exists",
            "no_immediate_failures"
        ],
        "restart_ecs_service": [
            "service_desired_count_updated",
            "tasks_running",
            "health_checks_passing",
            "error_rate_dropped"
        ]
    }
    
    def _verify_remediation(self, action: RemediationAction) -> VerificationResult:
        checklist = self.VERIFICATION_CHECKLISTS.get(action.action_type, [])
        verification_evidence = []
        
        for check in checklist:
            result = self._run_verification_check(check, action)
            verification_evidence.append({
                "check": check,
                "result": result.passed,
                "evidence": result.evidence_ref
            })
            if not result.passed:
                return VerificationResult(
                    passed=False,
                    failed_check=check,
                    evidence=verification_evidence
                )
        
        return VerificationResult(
            passed=True,
            evidence=verification_evidence
        )
```

---

#### 12. Cost-Aware Query Budgeting

**skill.md Requirement** (Line 227-228):
> cost-aware query budgeting:
> - Athena query limits, bytes scanned caps if possible

**Current State**:
- ❌ **Missing**: Athena query cost tracking
- ❌ **Missing**: Bytes scanned limits
- ❌ **Missing**: Query budget enforcement

**Impact**: Unbounded Athena queries could cause cost overruns.

**Required Changes**:
```python
# agent-host/src/agent_host/budget/query_budget.py
class QueryBudget:
    def __init__(self):
        self.max_athena_bytes_per_incident = 10_000_000_000  # 10GB
        self.max_athena_bytes_per_day = 100_000_000_000  # 100GB
        self.bytes_scanned_today = 0
    
    def check_athena_query(self, estimated_bytes: int) -> bool:
        """Check if Athena query is within budget."""
        if estimated_bytes > self.max_athena_bytes_per_incident:
            return False
        if self.bytes_scanned_today + estimated_bytes > self.max_athena_bytes_per_day:
            return False
        return True
    
    def record_athena_query(self, bytes_scanned: int):
        """Record Athena query cost."""
        self.bytes_scanned_today += bytes_scanned
```

---

### 🟢 Low Priority (Nice to Have)

#### 13. Tool Onboarding Templates

**skill.md Requirement** (Line 296-300):
> Templates:
> - `mcp-tool-template/` generator:
>   - schema + adapter + route + tests + docs

**Current State**:
- ❌ **Missing**: Tool template generator
- ❌ **Missing**: Workflow template generator

**Impact**: Slower onboarding of new AWS services.

**Recommendation**: Defer to Phase 1.

---

#### 14. UI Control Plane

**skill.md Requirement** (Line 264-271):
> Build a UI for:
> - incident feed and detail view (evidence + actions + verification)
> - policy management (tier toggles, allow-lists, approvals queue)
> - workflow registry management
> - trends: recurring issues, DQ health, cost savings, toil reduction

**Current State**:
- ❌ **Missing**: UI implementation

**Impact**: Harder to operate and manage the platform.

**Recommendation**: Defer to Phase 1+.

---

#### 15. Backward Compatibility Checks

**skill.md Requirement** (Line 304):
> backward compatibility checks (schema diff)

**Current State**:
- ❌ **Missing**: Schema versioning checks
- ❌ **Missing**: CI/CD backward compatibility tests

**Impact**: Breaking changes could affect production.

**Recommendation**: Defer to Phase 1, but add basic versioning now.

---

## Implementation Priority

### Must Fix Before Phase 0 Completion

1. ✅ **Action-Level Idempotency** (Critical)
2. ✅ **Correlation ID Propagation** (Critical)
3. ✅ **Circuit Breakers** (Critical)
4. ✅ **Job Envelope Standardization** (High)
5. ✅ **AWS API Throttling** (High)

### Should Fix Before Production

6. ✅ **Tool Version Contracts** (Critical)
7. ✅ **Heavy Task Isolation** (High)
8. ✅ **Platform Metrics** (Medium)
9. ✅ **Verification Checklists** (Medium)
10. ✅ **Multi-Account Support** (High)

### Can Defer to Phase 1

11. Distributed Tracing (Medium)
12. Cost-Aware Query Budgeting (Medium)
13. Tool Templates (Low)
14. UI Control Plane (Low)
15. Backward Compatibility Checks (Low)

---

## Testing Requirements

For each gap fix, add:

1. **Unit Tests**: Test the new component in isolation
2. **Integration Tests**: Test with real MCP servers
3. **End-to-End Tests**: Test complete flow with gap fix
4. **Regression Tests**: Ensure existing functionality still works

---

## Documentation Updates Required

1. Update `CURRENT_STATUS.md` with gap fixes
2. Update `CODE_FLOW.md` with new components
3. Update `ARCHITECTURE_DIAGRAM.md` with new architecture
4. Add `AUDIT_LOGGING.md` for audit trail documentation
5. Add `RATE_LIMITING.md` for throttling documentation

---

## Estimated Effort

| Gap | Priority | Effort | Dependencies |
|-----|----------|--------|--------------|
| Action-Level Idempotency | Critical | 4 hours | Action store DynamoDB table |
| Correlation ID Propagation | Critical | 6 hours | Audit logger, audit store |
| Circuit Breakers | Critical | 4 hours | None |
| Job Envelope Standardization | High | 6 hours | Multiple SQS queues |
| AWS API Throttling | High | 8 hours | Rate limiter, concurrency limiter |
| Tool Version Contracts | Critical | 6 hours | Tool registry |
| Heavy Task Isolation | High | 6 hours | Heavy task budget |
| Platform Metrics | Medium | 8 hours | CloudWatch integration |
| Verification Checklists | Medium | 4 hours | None |
| Multi-Account Support | High | 8 hours | STS client |

**Total Critical + High Priority**: ~52 hours (~1.5 weeks)

---

## Next Steps

1. **Review this document** with team
2. **Prioritize gaps** based on business needs
3. **Create tickets** for each gap fix
4. **Implement fixes** in priority order
5. **Update tests** and documentation
6. **Re-evaluate Phase 0 completion** after fixes

---

**Last Updated**: Current Session  
**Status**: Action Required - Critical gaps must be addressed before Phase 0 completion
