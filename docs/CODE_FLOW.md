# Code Flow & Process Lineage

**Complete technical documentation of the event processing flow from entry point to execution**

This document explains the exact code-level flow when an event occurs in the Ops AutoPilot system, including which modules and functions are called in sequence.

---

## 📋 Table of Contents

1. [High-Level Flow Overview](#high-level-flow-overview)
2. [Detailed Process Lineage](#detailed-process-lineage)
3. [Module & Function Reference](#module--function-reference)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Error Handling Flow](#error-handling-flow)

---

## High-Level Flow Overview

```
Event Source (SQS/File)
    ↓
main.py::main() / process_local_event()
    ↓
Dispatcher::dispatch()
    ↓
PipelineFailureWorkflow::handle()
    ↓
CoordinatorAgent::coordinate()
    ├─→ PipelineRCAAgent::investigate()
    │   ├─→ _gather_evidence() → MCP Clients → MCP Servers
    │   ├─→ _generate_rca() → LLM Provider
    │   └─→ _investigate_code_bug() → GitHub MCP Client (if CODE_REGRESSION)
    ├─→ PolicyEngine::evaluate_action()
    └─→ DecisionPacket creation
    ↓
RemediationAgent::execute_remediation() (if safe_to_autofix)
    ├─→ PolicyEngine::evaluate_action() (re-check)
    ├─→ _execute_action() → MCP Clients → MCP Servers
    └─→ _verify_remediation()
    ↓
format_decision_summary() → Human-readable output
```

---

## Detailed Process Lineage

### Phase 1: Event Reception

#### 1.1 Entry Point: `agent-host/src/agent_host/main.py`

**Function**: `main()` or `process_local_event()`

**What Happens**:
- Parses command-line arguments (`--local-file` or `--sqs`)
- Loads event JSON from file or SQS message
- Parses event into `PipelineFailureEvent` Pydantic model
- Creates `Dispatcher` instance
- Calls `dispatcher.dispatch(event)`

**Code Location**:
```python
# agent-host/src/agent_host/main.py:17-70

def process_local_event(event_file: str):
    # Load event from file
    event_path = Path(event_file)
    with open(event_path, "r") as f:
        event_data = json.load(f)
    
    # Parse event
    event = PipelineFailureEvent(**event_data)
    
    # Process event
    dispatcher = Dispatcher()
    result = dispatcher.dispatch(event)
```

**Key Files**:
- `agent-host/src/agent_host/main.py` - Entry point
- `shared/src/shared/schemas/events.py` - Event schema definitions

---

### Phase 2: Event Routing

#### 2.1 Dispatcher: `agent-host/src/agent_host/dispatcher.py`

**Function**: `Dispatcher::dispatch(event: Event) -> WorkflowResult`

**What Happens**:
- Receives event (e.g., `PipelineFailureEvent`)
- Looks up workflow based on `event.event_type`
- Routes to appropriate workflow handler
- Returns `WorkflowResult` with incident ID

**Code Location**:
```python
# agent-host/src/agent_host/dispatcher.py:47-92

def dispatch(self, event: Event) -> Optional["WorkflowResult"]:
    event_type = event.event_type
    
    # Get workflow for this event type
    workflow = self.workflows.get(event_type)
    
    # Process event through workflow
    result = workflow.handle(event)
    
    return result
```

**Workflow Mapping**:
- `PIPELINE_FAILURE` → `PipelineFailureWorkflow`
- `API_FAILURE` → `APIFailureWorkflow`
- `DQ_CHECK_REQUEST` → `DQCheckWorkflow`
- etc.

**Key Files**:
- `agent-host/src/agent_host/dispatcher.py` - Event routing
- `agent-host/src/agent_host/workflows/pipeline_failure.py` - Pipeline failure handler

---

### Phase 3: Workflow Execution

#### 3.1 Pipeline Failure Workflow: `agent-host/src/agent_host/workflows/pipeline_failure.py`

**Function**: `PipelineFailureWorkflow::handle(event: PipelineFailureEvent) -> WorkflowResult`

**What Happens**:
1. Creates `CoordinatorAgent` instance
2. Calls `coordinator.coordinate(event)` to orchestrate investigation
3. Receives `DecisionPacket` from coordinator
4. If `safe_to_autofix` and `actions_allowed`:
   - Creates `RemediationPlan` from allowed actions
   - Calls `remediation_agent.execute_remediation(plan)`
5. Returns `WorkflowResult` with incident ID and decision packet

**Code Location**:
```python
# agent-host/src/agent_host/workflows/pipeline_failure.py:25-95

def handle(self, event: PipelineFailureEvent) -> WorkflowResult:
    # Step 1: Coordinator orchestrates investigation
    decision_packet = self.coordinator.coordinate(event)
    
    # Step 2: Execute remediation if safe to autofix
    if decision_packet.safe_to_autofix and decision_packet.actions_allowed:
        remediation_plan = RemediationPlan(...)
        remediation_result = self.remediation_agent.execute_remediation(remediation_plan)
    
    return WorkflowResult(
        success=True,
        incident_id=incident_id,
        decision_packet=decision_packet,
        remediation_result=remediation_result,
    )
```

**Key Files**:
- `agent-host/src/agent_host/workflows/pipeline_failure.py` - Workflow implementation
- `agent-host/src/agent_host/agents/coordinator.py` - Coordinator agent
- `agent-host/src/agent_host/agents/remediation_agent.py` - Remediation agent

---

### Phase 4: Coordinator Orchestration

#### 4.1 Coordinator Agent: `agent-host/src/agent_host/agents/coordinator.py`

**Function**: `CoordinatorAgent::coordinate(event) -> DecisionPacket`

**What Happens**:
1. **Idempotency Check**: Generates incident ID, checks if already processed
2. **Investigation**: Calls `_investigate(event)` to activate specialist agents
3. **Policy Evaluation**: Calls `_apply_policy()` to evaluate each recommended action
4. **Decision Building**: Creates `DecisionPacket` with:
   - Root cause analysis
   - Recommended actions
   - Actions allowed by policy
   - Actions blocked by policy
   - Safe to autofix flag
5. **Storage**: Stores decision packet via `IncidentStore`

**Code Location**:
```python
# agent-host/src/agent_host/agents/coordinator.py:64-149

def coordinate(self, event: PipelineFailureEvent | APIFailureEvent) -> DecisionPacket:
    # Step 1: Generate incident ID and check idempotency
    incident_id = self._generate_incident_id(event)
    if self.incident_store.exists(incident_id):
        return self._load_existing_decision(incident_id)
    
    # Step 2: Select and activate specialist agents
    investigation_result = self._investigate(event)
    
    # Step 3: Extract recommended actions
    recommended_actions = investigation_result.get("recommended_actions", [])
    
    # Step 4: Apply policy to each action
    actions_allowed, actions_blocked = self._apply_policy(
        recommended_actions, event, investigation_result
    )
    
    # Step 5: Build decision packet
    decision_packet = DecisionPacket(...)
    
    # Step 6: Store decision packet
    self._store_decision(incident_id, decision_packet, event)
    
    return decision_packet
```

**Sub-Functions Called**:
- `_investigate()` → Routes to specialist agents
- `_investigate_pipeline_failure()` → Activates `PipelineRCAAgent`
- `_apply_policy()` → Evaluates actions with `PolicyEngine`
- `_determine_human_needs()` → Identifies escalation needs

**Key Files**:
- `agent-host/src/agent_host/agents/coordinator.py` - Coordinator implementation
- `agent-host/src/agent_host/policy/engine.py` - Policy engine
- `agent-host/src/agent_host/state/incident_store.py` - Incident storage

---

### Phase 5: Specialist Agent Investigation

#### 5.1 Pipeline RCA Agent: `agent-host/src/agent_host/agents/pipeline_rca_agent.py`

**Function**: `PipelineRCAAgent::investigate(event: PipelineFailureEvent) -> PipelineIncidentAnalysis`

**What Happens**:
1. **Evidence Gathering**: Calls `_gather_evidence(event)`
   - Uses `orchestration_client` to call MCP server tools:
     - `get_execution_details` → Step Functions execution details
     - `get_execution_history` → Step Functions execution history
   - Stores evidence in `EvidencePack`
2. **RCA Generation**: Calls `_generate_rca(event, evidence)`
   - Loads prompt template from `prompts/rca_prompt.md`
   - Formats prompt with evidence data
   - Calls LLM provider with structured output schema
   - Maps LLM response to `PipelineIncidentAnalysis`
3. **Code Investigation** (if `CODE_REGRESSION` detected):
   - Calls `_investigate_code_bug(event, evidence, rca_result)`
   - Uses `github_client` to search code, read files, get commits
   - Uses LLM to identify likely bug location
   - Re-generates RCA with code analysis

**Code Location**:
```python
# agent-host/src/agent_host/agents/pipeline_rca_agent.py:50-83

def investigate(self, event: PipelineFailureEvent) -> PipelineIncidentAnalysis:
    # Step 1: Gather evidence
    evidence = self._gather_evidence(event)
    
    # Step 2: Store evidence
    self.evidence_store.save(incident_id, evidence)
    
    # Step 3: Generate initial RCA
    rca_result = self._generate_rca(event, evidence)
    
    # Step 4: If CODE_REGRESSION detected, investigate code
    if rca_result.classification == FailureClassification.CODE_REGRESSION:
        code_analysis = self._investigate_code_bug(event, evidence, rca_result)
        # Re-generate RCA with code evidence
        rca_result = self._generate_rca(event, evidence)
    
    return rca_result
```

**Evidence Gathering Flow**:
```python
# agent-host/src/agent_host/agents/pipeline_rca_agent.py:85-135

def _gather_evidence(self, event: PipelineFailureEvent) -> EvidencePack:
    evidence = EvidencePack(...)
    
    # Call orchestration MCP server
    exec_details_response = self.orchestration_client.call_tool(
        tool_name="get_execution_details",
        arguments={"execution_arn": event.execution_arn.value},
    )
    
    # Convert to ExecutionDetails model
    evidence.execution_details = ExecutionDetails(**exec_details_response.result)
    
    # Get execution history
    exec_history_response = self.orchestration_client.call_tool(
        tool_name="get_execution_history",
        arguments={"execution_arn": event.execution_arn.value},
    )
    
    evidence.execution_history = ExecutionHistory(**exec_history_response.result)
    
    return evidence
```

**LLM RCA Generation Flow**:
```python
# agent-host/src/agent_host/agents/pipeline_rca_agent.py:137-234

def _generate_rca(self, event: PipelineFailureEvent, evidence: EvidencePack):
    # Load prompt template
    prompt_template = self._load_prompt_template()
    
    # Format prompt with evidence
    prompt = self._format_prompt(prompt_template, event, evidence)
    
    # Call LLM with structured output
    result = self.llm.generate_structured(
        prompt=prompt,
        response_schema=response_schema,
        system_prompt="You are an expert DevOps engineer...",
        temperature=0.3,
    )
    
    # Map to PipelineIncidentAnalysis
    return PipelineIncidentAnalysis(...)
```

**Key Files**:
- `agent-host/src/agent_host/agents/pipeline_rca_agent.py` - RCA agent
- `agent-host/src/agent_host/mcp_client/base.py` - MCP client base
- `agent-host/src/agent_host/mcp_client/devtools.py` - GitHub MCP client
- `agent-host/src/agent_host/llm/factory.py` - LLM provider factory
- `agent-host/src/agent_host/prompts/rca_prompt.md` - RCA prompt template

---

### Phase 6: MCP Client Communication

#### 6.1 MCP Client Base: `agent-host/src/agent_host/mcp_client/base.py`

**Function**: `MCPClient::call_tool(tool_name, arguments) -> MCPResponse`

**What Happens**:
1. **Circuit Breaker Check**: Verifies circuit breaker allows request
2. **HTTP Request**: Makes POST request to MCP server `/tools` endpoint
3. **Retry Logic**: Retries on transient failures (exponential backoff)
4. **Error Handling**: Raises appropriate exceptions (`MCPConnectionError`, `MCPTimeoutError`, `MCPServerError`)
5. **Response Parsing**: Returns `MCPResponse` with result data

**Code Location**:
```python
# agent-host/src/agent_host/mcp_client/base.py:150-220 (approximate)

def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPResponse:
    # Check circuit breaker
    if not self.circuit_breaker.can_attempt():
        raise MCPConnectionError("Circuit breaker is OPEN")
    
    # Make HTTP request with retries
    for attempt in range(self.max_retries):
        try:
            response = self.client.post(
                f"{self.base_url}/tools",
                json={"tool": tool_name, "arguments": arguments},
                timeout=self.timeout,
            )
            
            # Record success
            self.circuit_breaker.record_success()
            
            return MCPResponse(**response.json())
            
        except httpx.TimeoutException:
            self.circuit_breaker.record_failure()
            raise MCPTimeoutError(...)
        except httpx.RequestError:
            self.circuit_breaker.record_failure()
            # Retry with exponential backoff
```

**MCP Server Endpoints**:
- `http://localhost:8001/tools` - Orchestration (Step Functions)
- `http://localhost:8002/tools` - Observability (CloudWatch)
- `http://localhost:8003/tools` - Data Execution (Glue/EMR)
- `http://localhost:8007/tools` - DevTools (GitHub)

**Key Files**:
- `agent-host/src/agent_host/mcp_client/base.py` - MCP client implementation
- `mcp-servers/orchestration-sfn/src/orchestration_sfn/app.py` - Orchestration MCP server
- `mcp-servers/observability-cloudwatch/src/observability_cloudwatch/app.py` - Observability MCP server

---

### Phase 7: Policy Evaluation

#### 7.1 Policy Engine: `agent-host/src/agent_host/policy/engine.py`

**Function**: `PolicyEngine::evaluate_action(action: RemediationAction) -> PolicyDecision`

**What Happens**:
1. **Tier Detection**: Identifies environment tier (PROD, STAGING, DEV, NONPROD)
2. **Allowlist Check**: Verifies target resource is in allowlist
3. **Deny List Check**: Verifies target resource is not in deny list
4. **Rule Evaluation**: Loads tier-specific rules from YAML files
5. **Action Type Check**: Evaluates if action type is allowed/denied
6. **Rate Limiting**: Checks hourly/daily rate limits
7. **Time Window**: Verifies action is within allowed time window
8. **Returns**: `PolicyDecision` with `allowed`, `reason`, `requires_approval`

**Code Location**:
```python
# agent-host/src/agent_host/policy/engine.py:80-150 (approximate)

def evaluate_action(self, action: RemediationAction) -> PolicyDecision:
    # Detect tier
    tier = self.tier_detector.detect_tier(action.target, action.tier)
    
    # Check allowlist
    if not self._check_allowlist(action.target, tier):
        return PolicyDecision(allowed=False, reason="Resource not in allowlist")
    
    # Check deny list
    if self._check_deny_list(action.target, tier):
        return PolicyDecision(allowed=False, reason="Resource in deny list")
    
    # Load tier-specific rules
    tier_rules = self.rules.get("tiers", {}).get(tier.value, {})
    
    # Evaluate action type
    action_rules = tier_rules.get("actions", {}).get(action.action_type, {})
    
    # Check rate limits
    if not self._check_rate_limit(action, tier):
        return PolicyDecision(allowed=False, reason="Rate limit exceeded")
    
    # Check time window
    if not self._check_time_window(action, tier):
        return PolicyDecision(allowed=False, reason="Outside allowed time window")
    
    return PolicyDecision(allowed=True, reason="Action allowed by policy")
```

**Policy Rules Location**:
- `agent-host/src/agent_host/policy/rules/prod.yaml` - Production rules
- `agent-host/src/agent_host/policy/rules/nonprod.yaml` - Nonprod rules
- `agent-host/src/agent_host/policy/rules/allowlists.yaml` - Resource allowlists

**Key Files**:
- `agent-host/src/agent_host/policy/engine.py` - Policy engine
- `agent-host/src/agent_host/policy/tiers.py` - Tier detection
- `agent-host/src/agent_host/policy/rules/*.yaml` - Policy rules

---

### Phase 8: Remediation Execution

#### 8.1 Remediation Agent: `agent-host/src/agent_host/agents/remediation_agent.py`

**Function**: `RemediationAgent::execute_remediation(plan: RemediationPlan) -> RemediationResult`

**What Happens**:
1. **Policy Re-Check**: Re-evaluates each action with policy engine (safety check)
2. **Action Execution**: For each allowed action:
   - `retry_execution` / `start_execution` → Calls orchestration MCP server `start_execution` tool
   - `stop_execution` → Calls orchestration MCP server `stop_execution` tool
   - `restart_service` → Placeholder (not implemented in Phase 0)
3. **Verification**: Calls `_verify_remediation()` to check execution status
4. **Returns**: `RemediationResult` with actions taken, failed, and verification status

**Code Location**:
```python
# agent-host/src/agent_host/agents/remediation_agent.py:53-125

def execute_remediation(self, plan: RemediationPlan) -> RemediationResult:
    actions_taken = []
    actions_failed = []
    
    for action in plan.actions:
        # Step 1: Policy check
        policy_result = self._check_policy(action, plan)
        if not policy_result.allowed:
            actions_failed.append(...)
            continue
        
        # Step 2: Execute action
        execution_result = self._execute_action(action, plan)
        
        if execution_result["success"]:
            actions_taken.append(...)
        else:
            actions_failed.append(...)
    
    # Step 3: Verify remediation
    verification = self._verify_remediation(plan, actions_taken)
    
    return RemediationResult(...)
```

**Action Execution Flow**:
```python
# agent-host/src/agent_host/agents/remediation_agent.py:187-247

def _execute_retry_or_start(self, action: RecommendedAction, plan: RemediationPlan):
    # Get state machine ARN
    state_machine_arn = action.parameters.get("state_machine_arn")
    
    # Call orchestration MCP server
    response = self.orchestration_client.call_tool(
        tool_name="start_execution",
        arguments={
            "state_machine_arn": state_machine_arn,
            "input_data": input_data,
            "name": action.parameters.get("execution_name"),
        },
    )
    
    return {
        "success": True,
        "details": {"execution_arn": response.result.get("executionArn")},
    }
```

**Key Files**:
- `agent-host/src/agent_host/agents/remediation_agent.py` - Remediation agent
- `mcp-servers/orchestration-sfn/src/orchestration_sfn/app.py` - Orchestration MCP server

---

### Phase 9: Summary Generation

#### 9.1 Summary Formatter: `agent-host/src/agent_host/utils/summary.py`

**Function**: `format_decision_summary(decision_packet, remediation_result, evidence_dir) -> str`

**What Happens**:
- Formats `DecisionPacket` into human-readable text
- Includes: incident ID, what happened, root cause, recommended actions, policy evaluation, remediation status, human intervention needs, evidence references
- Returns formatted string with box-drawing characters

**Code Location**:
```python
# agent-host/src/agent_host/utils/summary.py:10-231

def format_decision_summary(
    decision_packet: DecisionPacket,
    remediation_result: Optional[RemediationResult] = None,
    evidence_dir: Optional[str] = None,
) -> str:
    lines = []
    
    # Header
    lines.append("╔" + "═" * 70 + "╗")
    lines.append("║" + " " * 20 + "INCIDENT SUMMARY" + " " * 33 + "║")
    
    # Basic Info
    lines.append(f"Incident ID: {decision_packet.incident_id}")
    
    # What Happened
    lines.append("━" * 72)
    lines.append("WHAT HAPPENED")
    lines.append(decision_packet.what_happened)
    
    # Root Cause Analysis
    lines.append("ROOT CAUSE ANALYSIS")
    lines.append(f"Classification: {decision_packet.root_cause.get('classification')}")
    
    # ... (more sections)
    
    return "\n".join(lines)
```

**Called From**:
```python
# agent-host/src/agent_host/main.py:51-59

if result.decision_packet:
    from agent_host.utils.summary import format_decision_summary
    
    summary = format_decision_summary(
        decision_packet=result.decision_packet,
        remediation_result=result.remediation_result,
        evidence_dir=config.local_evidence_dir,
    )
    print("\n" + summary)
```

**Key Files**:
- `agent-host/src/agent_host/utils/summary.py` - Summary formatter
- `agent-host/src/agent_host/main.py` - Prints summary

---

## Module & Function Reference

### Core Modules

| Module | File | Key Functions |
|--------|------|---------------|
| **Main Entry** | `agent-host/src/agent_host/main.py` | `main()`, `process_local_event()`, `process_sqs_messages()` |
| **Dispatcher** | `agent-host/src/agent_host/dispatcher.py` | `dispatch()`, `get_workflow()` |
| **Workflow** | `agent-host/src/agent_host/workflows/pipeline_failure.py` | `handle()` |
| **Coordinator** | `agent-host/src/agent_host/agents/coordinator.py` | `coordinate()`, `_investigate()`, `_apply_policy()` |
| **Pipeline RCA** | `agent-host/src/agent_host/agents/pipeline_rca_agent.py` | `investigate()`, `_gather_evidence()`, `_generate_rca()`, `_investigate_code_bug()` |
| **Remediation** | `agent-host/src/agent_host/agents/remediation_agent.py` | `execute_remediation()`, `_execute_action()`, `_verify_remediation()` |
| **Policy Engine** | `agent-host/src/agent_host/policy/engine.py` | `evaluate_action()`, `_check_allowlist()`, `_check_rate_limit()` |
| **MCP Client** | `agent-host/src/agent_host/mcp_client/base.py` | `call_tool()`, `_make_request()` |
| **Incident Store** | `agent-host/src/agent_host/state/incident_store.py` | `save_decision_packet()`, `load_decision_packet()`, `exists()` |
| **Summary** | `agent-host/src/agent_host/utils/summary.py` | `format_decision_summary()` |

### MCP Server Modules

| Server | File | Key Functions |
|--------|------|---------------|
| **Orchestration** | `mcp-servers/orchestration-sfn/src/orchestration_sfn/app.py` | `get_execution_details()`, `start_execution()`, `stop_execution()` |
| **Observability** | `mcp-servers/observability-cloudwatch/src/observability_cloudwatch/app.py` | `query_logs()`, `get_log_events()`, `get_metrics()` |
| **Data Execution** | `mcp-servers/data-execution-glue-emr/src/data_execution/app.py` | `get_glue_job_run()`, `get_emr_step()` |
| **DevTools** | `mcp-servers/devtools-github/src/devtools_github/app.py` | `search_code()`, `read_file()`, `get_recent_commits()` |

---

## Data Flow Diagrams

### Complete Event Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EVENT RECEPTION                                             │
│    main.py::process_local_event()                              │
│    - Loads JSON from file                                      │
│    - Parses to PipelineFailureEvent                            │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. EVENT ROUTING                                                │
│    Dispatcher::dispatch()                                       │
│    - Maps event_type → workflow                                 │
│    - Returns WorkflowResult                                     │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. WORKFLOW EXECUTION                                           │
│    PipelineFailureWorkflow::handle()                            │
│    - Creates CoordinatorAgent                                   │
│    - Calls coordinator.coordinate()                             │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. COORDINATOR ORCHESTRATION                                    │
│    CoordinatorAgent::coordinate()                               │
│    ├─→ _investigate() → PipelineRCAAgent                       │
│    ├─→ _apply_policy() → PolicyEngine                           │
│    └─→ DecisionPacket creation                                  │
└────────────────────┬──────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│ 5. RCA INVESTIGATION     │ 6. POLICY EVAL    │
│ PipelineRCAAgent        │ PolicyEngine      │
│ - _gather_evidence()    │ - evaluate_action()│
│ - _generate_rca()       │ - Check allowlist │
│ - LLM call              │ - Check rate limit│
└──────────────────┘      └──────────────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. REMEDIATION EXECUTION (if safe_to_autofix)                  │
│    RemediationAgent::execute_remediation()                      │
│    - Policy re-check                                            │
│    - _execute_action() → MCP Clients → MCP Servers              │
│    - _verify_remediation()                                      │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. SUMMARY GENERATION                                           │
│    format_decision_summary()                                    │
│    - Formats DecisionPacket                                     │
│    - Prints human-readable output                               │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Client Communication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent (e.g., PipelineRCAAgent)                                 │
│   self.orchestration_client.call_tool("get_execution_details") │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCPClient::call_tool()                                          │
│ - Check circuit breaker                                          │
│ - Make HTTP POST to /tools                                       │
│ - Retry on failure (exponential backoff)                          │
│ - Return MCPResponse                                            │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP Server (e.g., orchestration-sfn)                           │
│   POST /tools                                                    │
│   {                                                              │
│     "tool": "get_execution_details",                             │
│     "arguments": {"execution_arn": "..."}                        │
│   }                                                              │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ AWS API (e.g., Step Functions)                                   │
│   boto3.client("stepfunctions").describe_execution()            │
└────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Response flows back through chain                                │
│   AWS API → MCP Server → MCP Client → Agent                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

### Error Propagation

```
Exception in Agent
    ↓
Caught by Workflow
    ↓
Logged and wrapped in WorkflowResult(success=False, reason="...")
    ↓
Returned to Dispatcher
    ↓
Logged and returned to main.py
    ↓
Printed to console / logged to CloudWatch
```

### Circuit Breaker Flow

```
MCP Client Call
    ↓
Circuit Breaker Check
    ├─→ CLOSED: Allow request
    ├─→ OPEN: Reject immediately (raise MCPConnectionError)
    └─→ HALF_OPEN: Allow one test request
         ├─→ Success: Transition to CLOSED
         └─→ Failure: Transition back to OPEN
```

### LLM Fallback Flow

```
PipelineRCAAgent::_generate_rca()
    ↓
Try: LLM.generate_structured()
    ├─→ Success: Return PipelineIncidentAnalysis
    └─→ Exception: Catch error
         ↓
         _generate_rca_fallback()
         ↓
         Rule-based classification
         ↓
         Return PipelineIncidentAnalysis (lower confidence)
```

---

## Key Data Structures

### Event Flow

```
PipelineFailureEvent (Pydantic)
    ↓
EvidencePack (Pydantic)
    ↓
PipelineIncidentAnalysis (Pydantic)
    ↓
DecisionPacket (Pydantic)
    ↓
RemediationPlan (Pydantic)
    ↓
RemediationResult (Pydantic)
    ↓
WorkflowResult (Pydantic)
```

### MCP Communication

```
MCPClient.call_tool(tool_name, arguments)
    ↓
HTTP POST to /tools
    ↓
MCPResponse (Pydantic)
    ↓
result: dict (tool-specific response)
```

---

## Configuration Flow

### Environment Detection

```
main.py starts
    ↓
config.py::Config.__init__()
    ↓
Detect environment:
    ├─→ Local: Check for local files, use localhost URLs
    └─→ AWS: Check for ECS metadata, use service discovery
    ↓
Set MCP server URLs, storage paths, SQS queues
```

---

## Summary

This document provides a complete code-level trace of the event processing flow in Ops AutoPilot. When an event occurs:

1. **Entry**: `main.py` receives event (file or SQS)
2. **Routing**: `Dispatcher` routes to appropriate workflow
3. **Orchestration**: `CoordinatorAgent` coordinates investigation
4. **Investigation**: `PipelineRCAAgent` gathers evidence and generates RCA
5. **Policy**: `PolicyEngine` evaluates actions
6. **Remediation**: `RemediationAgent` executes allowed actions
7. **Output**: Human-readable summary is printed

All components are modular, testable, and follow clear separation of concerns.

---

**Last Updated**: Current Session  
**Version**: Phase 0 MVP
