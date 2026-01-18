# Implementation Plan: ops-autopilot

## Executive Summary

**Goal**: Build an Agentic AI Ops AutoPilot to monitor and remediate 300+ Glue/EMR PySpark pipelines orchestrated by Step Functions/Airflow, with continuous data quality monitoring, automated RCA, cost optimization, and remediation capabilities.

**Architecture**: Agent Host (brain) + MCP Servers (tools) + LLM (reasoning) on AWS

---

## Tech Stack

**Recommended pragmatic defaults** for consistent, maintainable implementation:

### Core Languages & Frameworks
- **Language**: **Python 3.11+** (fast iteration, excellent AWS SDK support)
- **Agent Host**: Python application (long-running service)
- **MCP Servers**: **Python FastAPI** (keep consistent across all MCP servers)
  - Alternative: Node.js (acceptable, but Python everywhere is easier to maintain)

### Infrastructure & Deployment
- **Agent Host runtime**: **ECS Fargate service** (long-running worker, not Lambda)
- **Queue**: **SQS** (separate queues by priority: incidents, dq, cost, daily)
- **State store**: **DynamoDB** (workflow registry, incidents, baselines, fingerprints)
- **Evidence store**: **S3** (evidence bundles, daily digests)
- **IaC**: **Terraform** or **CDK** (pick what your org already uses)

### AI/LLM
- **LLM Provider Options** (configurable, with abstraction layer):
  - **Amazon Bedrock** (preferred on AWS, supports Claude via Bedrock)
  - **OpenAI** (GPT-4, GPT-3.5-turbo) - Direct API
  - **Anthropic Claude** (Claude 3 Opus/Sonnet/Haiku) - Direct API or via Bedrock
  - **Google Gemini** (Gemini Pro, Gemini Ultra) - Direct API
  - Support multiple providers via abstraction layer (choose any provider per workflow/agent)

**Configuration**: 
- Default provider set via environment variable: `LLM_PROVIDER=bedrock|openai|anthropic|gemini`
- Per-workflow/provider overrides possible (e.g., use cheaper model for simple tasks, premium for RCA)
- Cost optimization: Use cheaper models (GPT-3.5, Gemini) for classification, premium models (GPT-4, Claude Opus) for complex RCA

### AWS Services Used
- **Compute**: ECS Fargate (Agent Host + MCP servers)
- **Orchestration**: EventBridge (event routing) → SQS (queueing)
- **Storage**: DynamoDB (hot state), S3 (cold evidence)
- **Observability**: CloudWatch Logs, CloudWatch Metrics
- **Orchestration Tools**: Step Functions, Glue, EMR (monitored)
- **Runtime**: ECS Fargate (FastAPI services - monitored)
- **Data Quality**: Athena, Glue Data Catalog

### Python Dependencies (Key Libraries)
- **Web Framework**: FastAPI (MCP servers)
- **AWS SDK**: boto3
- **Data Validation**: Pydantic (schemas, type safety)
- **HTTP Client**: httpx or requests (MCP client in Agent Host)
- **LLM Clients**: 
  - boto3 (Amazon Bedrock - Claude models)
  - openai (OpenAI - GPT models)
  - anthropic (Anthropic Claude - direct API)
  - google-generativeai (Google Gemini)
- **Configuration**: pydantic-settings or python-dotenv
- **Logging**: structlog (structured logging)

### Development Tools
- **Package Management**: Poetry or uv (recommended) or pip + requirements.txt
- **Testing**: pytest
- **Code Quality**: black, ruff, mypy
- **Local Development**: docker-compose (run MCP servers locally)

---

## System Goals & Success Criteria

### Primary Objectives
1. **Keep 300+ workflows healthy** - Proactive monitoring, early failure detection
2. **Ensure data quality continuously** - Automated DQ checks, validation, alerts
3. **Reduce MTTR (Mean Time To Resolution)** - Automated RCA, actionable remediation plans
4. **Cost optimization** - Resource rightsizing, waste detection, recommendations
5. **Actionable remediation** - Create and optionally execute fix plans

### Success Metrics
- **MTTR reduction**: Target < 15 minutes for common pipeline failures (vs current ~2 hours)
- **Detection time**: < 2 minutes from failure to incident creation
- **DQ coverage**: 100% of critical tables covered by automated checks
- **Cost savings**: 15-20% reduction through rightsizing recommendations
- **Automation rate**: 70%+ of incidents auto-remediated without human intervention

---

## Architecture Overview

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Event Sources                         │
│  Step Functions | Glue/EMR | ECS APIs | CloudWatch      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              EventBridge → SQS Queues                   │
│  (incidents | dq_checks | cost_scan | daily_sweep)     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Host (Coordinator)                   │
│  • Dispatcher (routes events → workflows)              │
│  • Workflows (pipeline_failure, api_failure, etc.)     │
│  • Agents (RCA, remediation, cost, DQ)                 │
│  • Policy Engine (gate write actions)                  │
│  • State Store (DynamoDB + S3 evidence)                │
└───────────────┬───────────────────────┬─────────────────┘
                │                       │
                │ MCP Protocol          │ MCP Protocol
                │ (HTTP/JSON)           │ (HTTP/JSON)
                ▼                       ▼
┌──────────────────────┐   ┌──────────────────────────────┐
│   MCP Servers        │   │      LLM Provider            │
│  (Domain Tools)      │   │  (RCA, Planning, PR Gen)     │
├──────────────────────┤   └──────────────────────────────┘
│ • orchestration-sfn  │
│ • observability-cw   │
│ • data-execution     │
│ • runtime-ecs        │
│ • data-quality       │
│ • finops             │
│ • devtools-github    │
│ • chatops            │
└──────────────────────┘
```

### Key Design Principles

1. **MCP Servers are "dumb adapters"** - No business logic, just AWS API wrappers
2. **Agent Host contains all reasoning** - LLM calls, workflow orchestration, decision-making
3. **Agent Host is long-running** - ECS Fargate service (not stateless Lambda) for persistent state and multi-step reasoning
4. **Structured outputs required** - All LLM outputs must be JSON (not free text) for programmatic handling
5. **Policy-gated writes** - All remediation actions require policy approval
6. **Event-driven** - Asynchronous processing via SQS
7. **Evidence-based** - All decisions backed by collected evidence (logs, metrics, traces)
8. **Memory/learning enabled** - Remembers past incidents, fingerprints, successful remediations

### Deployment Model

**Agent Host**: ECS Fargate service (always-on)
- Long-running process that continuously polls SQS
- Maintains in-memory state (workflow registry, active investigations)
- Can scale horizontally (multiple tasks processing different queues)
- Easy to update without losing state (graceful restarts)

**MCP Servers**: ECS Fargate services (stateless)
- FastAPI HTTP servers exposing MCP protocol
- Can scale independently based on tool call volume
- Stateless by design (all state in AWS services)

**Why not Lambda?**
- Agent Host needs persistent state for multi-step reasoning
- LLM reasoning can take 30-60 seconds (Lambda timeout concerns)
- Long-running tool orchestration loops (collect evidence → analyze → decide → act)
- Memory/learning requires long-running process with state

---

## Data Flow: Pipeline Failure Example (Detailed Agent Host Flow)

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Event Detection & Ingestion                     │
└─────────────────────────────────────────────────────────┘
Step Functions execution fails
   ↓
EventBridge rule triggers (state = FAILED)
   ↓
Event → SQS FIFO queue (incidents.fifo)

┌─────────────────────────────────────────────────────────┐
│ STEP 2: Agent Host Event Intake                         │
└─────────────────────────────────────────────────────────┘
Agent Host (ECS Fargate) long-running process polls SQS
   ↓
Dispatcher consumes message: {"type": "PIPELINE_FAILURE", "execution_arn": "..."}
   ↓
Dispatcher routes to pipeline_failure workflow

┌─────────────────────────────────────────────────────────┐
│ STEP 3: Workflow Orchestration                          │
└─────────────────────────────────────────────────────────┘
Workflow checks incident_store (idempotency check)
   ↓
Workflow activates pipeline_rca_agent

┌─────────────────────────────────────────────────────────┐
│ STEP 4: Tool Orchestration (MCP Calls)                  │
└─────────────────────────────────────────────────────────┘
Agent coordinates multiple MCP tool calls:

Round 1: Gather basic context
  - mcp_client.orchestration.get_execution_details(execution_arn)
  - mcp_client.orchestration.get_execution_history(execution_arn)

Round 2: Gather evidence (based on failure type)
  - mcp_client.observability.query_logs(error_patterns, time_range)
  - mcp_client.observability.get_metrics(glue_job_metrics)
  - mcp_client.data_execution.get_glue_job_run(job_name, run_id)

Agent collects all results → builds evidence pack
   ↓
Agent checks incident_store for similar past incidents (fingerprint matching)

┌─────────────────────────────────────────────────────────┐
│ STEP 5: Reasoning (LLM with Structured Output)          │
└─────────────────────────────────────────────────────────┘
Agent calls LLM with:
  - Prompt template: prompts/rca_prompt.md
  - Context: evidence pack, past incidents, workflow metadata
  - Schema: Force JSON output with classification, root_cause, confidence, actions
   ↓
LLM returns structured RCA:
{
  "classification": "DEPENDENCY_OUTAGE",
  "confidence": 0.82,
  "root_cause": "FastAPI service returned 503...",
  "recommended_actions": ["restart_ecs_service", "increase_desired_count"],
  "safe_to_autofix": true
}

┌─────────────────────────────────────────────────────────┐
│ STEP 6: Policy Evaluation (Safety Gate)                 │
└─────────────────────────────────────────────────────────┘
Policy engine evaluates: safe_to_autofix?
  - Checks tier: prod vs nonprod
  - Checks allowlist: Is state_machine_arn in allowed list?
  - Checks time window: Is it peak hours?
  - Checks circuit breaker: Too many recent failures?
   ↓
Decision: allowed=True (nonprod, in allowlist, off-peak)

┌─────────────────────────────────────────────────────────┐
│ STEP 7: Remediation (Policy-Gated)                      │
└─────────────────────────────────────────────────────────┘
If allowed: remediation_agent creates execution plan
  Plan: {"action": "start_execution", "state_machine_arn": "..."}
   ↓
Policy check: evaluate_action("start_execution", context) → allowed=True
   ↓
Execute via MCP: mcp_client.orchestration.start_execution(...)
   ↓
Verification: Agent waits 30s, checks execution status

┌─────────────────────────────────────────────────────────┐
│ STEP 8: Evidence & State Storage                        │
└─────────────────────────────────────────────────────────┘
Evidence pack written to S3:
  s3://evidence-bucket/<incident_id>/evidence.json
  - Original event
  - All MCP tool results
  - RCA packet
  - Remediation plan + result
   ↓
Incident record written to DynamoDB:
  - Incident ID, timestamp, workflow name
  - Fingerprint (for future matching)
  - Classification, root_cause
  - Remediation outcome
  - TTL: 90 days

┌─────────────────────────────────────────────────────────┐
│ STEP 9: Notification & Learning                         │
└─────────────────────────────────────────────────────────┘
ChatOps notification via mcp_client.chatops:
  - Slack: Human-readable summary + evidence links
  - Jira: Ticket created (if escalation needed)
   ↓
Learning updates:
  - Update baselines: Normal metrics for this workflow
  - Store fingerprint: Error pattern → successful remediation mapping
  - Update registry: Mark workflow as "recently failed" (for daily sweep)
```

**Total time**: Target < 15 minutes from detection to remediation (or notification if blocked)

---

## Implementation Phases

### Phase 0: Foundation (MVP - Weeks 1-2)
**Goal**: End-to-end pipeline failure detection → RCA generation

**Recommended "Minimal Build" MVP Configuration**:
- ✅ **Coordinator Agent** - Basic orchestration
- ✅ **Pipeline RCA Agent** - Step Functions/Glue failure investigation
- ✅ **Data Quality Agent** - Light checks (optional in MVP, but recommended)
- ✅ **Runtime/API Agent** - ECS FastAPI service health
- ✅ **Remediation Agent** - Basic fix execution (policy-gated)
- ✅ **Policy Engine** - Rule evaluation
- ✅ **Evidence Store** - S3 + DynamoDB

**Defer to later phases**:
- Code Fix Agent (Phase 6)
- Cost & Capacity Agent (Phase 4)
- Weekly deep review (Phase 4)

**Deliverables**:
- ✅ Agent Host: dispatcher, coordinator, pipeline_failure workflow
- ✅ Coordinator Agent: Basic orchestration, policy gating
- ✅ Pipeline RCA Agent: Evidence collection, LLM-based RCA
- ✅ Remediation Agent: Policy-gated fix execution
- ✅ MCP orchestration-sfn: list, describe, get_history, start_execution tools
- ✅ MCP observability-cw: query_logs, get_metrics tools
- ✅ MCP data-execution: get_glue_job_run, get_emr_step tools (if needed)
- ✅ Shared schemas: events, evidence, rca
- ✅ Local development setup (docker-compose)
- ✅ Evidence storage (local file → S3 later)

**Success Criteria**: 
- Can process a sample pipeline_failure.json event
- Coordinator activates Pipeline RCA Agent → collects evidence
- Generates structured RCA JSON with classification, root cause, confidence
- Policy engine gates write actions (nonprod allows, prod denies)
- Prints human-readable summary

---

### Phase 1: Production Hardening (Weeks 3-4)
**Goal**: Deploy MVP to AWS, add reliability, monitoring

**Deliverables**:
- ✅ Terraform infra: ECS services, SQS, EventBridge rules
- ✅ DynamoDB state store (workflow registry, incidents)
- ✅ S3 evidence bucket with lifecycle policies
- ✅ CloudWatch alarms for Agent Host/MCP health
- ✅ IAM roles with least-privilege per MCP server
- ✅ Error handling, retries, dead-letter queues

**Success Criteria**:
- System runs 24/7 processing real Step Functions events
- No data loss (all events processed)
- MTTR < 30 minutes for common failures

---

### Phase 2: Remediation Automation (Weeks 5-6)
**Goal**: Enable policy-gated auto-remediation

**Deliverables**:
- ✅ Policy engine: rule evaluation, tiers (prod/nonprod)
- ✅ Remediation agent: fix plans, execution
- ✅ MCP orchestration-sfn: start_execution(), stop_execution()
- ✅ Verification step: confirm fix success
- ✅ Audit logging: all write actions to CloudTrail/DynamoDB

**Success Criteria**:
- 50%+ of nonprod failures auto-remediated
- 0 accidental prod writes (policy enforcement)
- All actions auditable

---

### Phase 3: Data Quality (Weeks 7-8)
**Goal**: Continuous DQ monitoring via Athena

**Deliverables**:
- ✅ MCP data-quality-athena: query, validate, catalog tools
- ✅ DQ workflow: scheduled checks, drift detection
- ✅ Data quality agent: analyze violations, propose fixes
- ✅ Integration with pipeline_failure (check DQ post-fix)

**Success Criteria**:
- 100% of critical tables have DQ checks
- Violations detected within 1 hour of data arrival
- Automated remediation for simple issues (missing partitions, etc.)

---

### Phase 4: Cost Optimization (Weeks 9-10)
**Goal**: Rightsizing recommendations, waste detection

**Deliverables**:
- ✅ MCP finops: cost_explorer queries, rightsizing API
- ✅ Cost workflow: daily scans, anomaly detection
- ✅ Cost agent: generate recommendations
- ✅ Integration with remediation (auto-downsize idle resources)

**Success Criteria**:
- Weekly cost reports with actionable recommendations
- 10%+ cost savings identified
- Auto-rightsizing for nonprod environments

---

### Phase 5: API & ECS Monitoring (Weeks 11-12)
**Goal**: Extend to ECS Fargate FastAPI services

**Deliverables**:
- ✅ MCP runtime-ecs: ECS/ALB tools
- ✅ API failure workflow: 5xx, latency, crash-loop detection
- ✅ API incident agent: trace requests, correlate logs
- ✅ Integration with existing observability MCP

**Success Criteria**:
- ECS service failures detected and analyzed
- API latency anomalies trigger incidents
- Correlation between API and pipeline failures

---

### Phase 6: Advanced Features (Weeks 13+)
**Goal**: PR automation, learning, multi-tenant

**Deliverables**:
- ✅ MCP devtools-github: PR creation, code analysis
- ✅ Code fix agent: propose code changes via PR
- ✅ Learning system: store incident patterns, improve RCA
- ✅ Multi-tenant: tenant isolation, per-tenant policies

---

## Component Responsibilities

### Agent Host (`agent-host/`) - The Brain + Nervous System

**Architecture**: Long-running ECS Fargate service (not stateless Lambda)

> **Key Principle**: Agent Host = autonomous operations worker that decides, coordinates, applies policy, and learns over time.

#### 6 Core Responsibilities

##### 1. Event Intake / Work Dispatcher
**Input Sources**:
- EventBridge → SQS (Step Functions failures, Glue failures, ECS alarms)
- Scheduled jobs (daily sweep, weekly cost review)

**Event Types**:
- `PIPELINE_FAILURE` - Step Functions/Glue/EMR execution failures
- `DQ_CHECK_REQUEST` - Data quality validation requests
- `API_FAILURE` - ECS FastAPI service failures
- `DAILY_SWEEP` - Proactive health checks
- `COST_WEEKLY_REVIEW` - Cost optimization analysis

**Components**:
- `main.py`: Long-running SQS polling loop (always-on service)
- `dispatcher.py`: Routes event types → workflows based on event schema

---

##### 2. Tool Orchestration (MCP Client Runtime)
**Connects to multiple MCP servers**:
- `mcp-orchestration` (Step Functions)
- `mcp-data-execution` (Glue/EMR)
- `mcp-observability` (CloudWatch)
- `mcp-runtime` (ECS)
- `mcp-data-quality` (Athena)
- `mcp-finops` (cost optimization)
- `mcp-devtools` (GitHub)
- `mcp-chatops` (Slack/Jira)

**Responsibilities**:
- Chooses which tools to call based on investigation needs
- Orders tool calls logically (e.g., get execution details → query related logs)
- Handles retries safely (exponential backoff, circuit breakers)
- Collects and aggregates tool results into evidence packs

**Components**:
- `mcp_client/base.py`: HTTP client for MCP protocol (retries, timeouts, error handling)
- `mcp_client/orchestration.py`: Typed client for orchestration MCP
- `mcp_client/observability.py`: Typed client for observability MCP
- (Similar for other MCP domains)

---

##### 3. Reasoning + Decision Engine (LLM-driven)
**Purpose**: Performs "human-like ops thinking" using structured outputs

**LLM Tasks**:
- Classify incident type
- Infer likely root cause
- Decide what evidence is missing and fetch it
- Generate remediation plan
- Decide whether to auto-execute or escalate
- Draft PR patch suggestions

**CRITICAL**: All LLM outputs must be **structured (JSON)**, not free text.

**Example RCA Agent Output**:
```json
{
  "classification": "DEPENDENCY_OUTAGE",
  "confidence": 0.82,
  "root_cause": "FastAPI service returned 503 causing pipeline failures",
  "recommended_actions": ["restart_ecs_service", "increase_desired_count_temporarily"],
  "safe_to_autofix": true,
  "evidence_gaps": ["need_ecs_task_logs", "need_alb_metrics"]
}
```

**Components**:
- `agents/pipeline_rca_agent.py`: Pipeline failure investigation
- `agents/remediation_agent.py`: Fix plan generation and execution
- `agents/data_quality_agent.py`: DQ violation analysis
- `agents/cost_agent.py`: Cost optimization recommendations
- `agents/code_fix_agent.py`: Code change proposals
- `prompts/*.md`: Prompt templates for structured outputs

---

##### 4. Policy + Guardrails (Safety Brain)
**Purpose**: Makes autonomy production-safe

**Policy Enforcements**:
- **Write action gating**: Which actions allowed in prod vs nonprod
- **Max retry counts**: Prevent infinite reruns
- **Blast radius control**: Limit concurrent remediation actions
- **Time windows**: Don't redeploy at peak hours
- **Circuit breakers**: Too many failures → notify-only mode

**Components**:
- `policy/engine.py`: Rule evaluation engine (`evaluate_action(action, context) -> PolicyDecision`)
- `policy/tiers.py`: Tier definitions (prod, nonprod, dev)
- `policy/rules/prod.yaml`: Production rules (default deny)
- `policy/rules/nonprod.yaml`: Non-prod rules (allowlist-based)
- `policy/rules/allowlists.yaml`: Resource allowlists per tier

**Policy Decision Flow**:
```python
action = "start_execution"
context = {"tier": "prod", "state_machine_arn": "arn:..."}
decision = policy_engine.evaluate_action(action, context)
# Returns: PolicyDecision(allowed=False, reason="prod tier denies start_execution")
```

---

##### 5. Memory / State Store (Learning Over Time)
**Purpose**: Remember patterns, learn from incidents, maintain baselines

**What the Host Remembers**:
- Which workflows fail frequently (incident history)
- Fingerprints of known errors (error pattern matching)
- What remediation worked last time (success patterns)
- What "normal" dataset metrics look like (baselines)

**Storage Strategy**:
- **DynamoDB** (hot data):
  - Workflow registry (metadata for 300+ workflows)
  - Incident history (recent incidents, fingerprints)
  - Baselines (expected metrics, normal patterns)
- **S3** (cold data):
  - Evidence packs (full logs, traces, snapshots)
  - Daily digests (aggregated insights)
  - Long-term learning data

**Components**:
- `state/registry.py`: Workflow metadata store (DynamoDB)
- `state/incident_store.py`: Incident history (DynamoDB with TTL)
- `state/baselines.py`: Normal patterns store (DynamoDB)
- `state/evidence_store.py`: Evidence pack writer (S3)

**Learning Example**:
```python
# Check if we've seen this error before
fingerprint = compute_error_fingerprint(error_log)
past_incident = incident_store.find_by_fingerprint(fingerprint)
if past_incident and past_incident.remediation_worked:
    # Use successful remediation from history
    plan = past_incident.remediation_plan
```

---

##### 6. Multi-Agent Coordination: Coordinator + Specialist Agents

**Pattern**: Coordinator Agent (manager) + Specialist Agents (do the deep work)

**Architecture**:
- **Coordinator Agent** (`agents/coordinator.py`): Manager that orchestrates specialist agents
- **Specialist Agents**: Domain experts that perform focused investigations

**Why This Pattern?**:
- Separates concerns: Coordinator = orchestration, Specialists = domain expertise
- Enables parallel agent execution for complex incidents
- Allows specialization: Each agent optimized for its domain
- Makes testing easier: Mock coordinator or mock specialists independently

---

---

### Coordinator Agent: The Manager

**Location**: `agents/coordinator.py`

**Purpose**: Orchestrates multiple specialist agents, applies policy gating, merges outputs into a single decision packet.

**Inputs**: Event from SQS (normalized by dispatcher)
- `PIPELINE_FAILURE`
- `API_FAILURE`
- `DQ_CHECK_REQUEST`
- `DAILY_SWEEP`
- `COST_DAILY_SCAN`

**Outputs**: Single "Decision Packet" (structured JSON):
```json
{
  "incident_id": "...",
  "what_happened": "Step Functions execution failed",
  "evidence_collected": [...],
  "root_cause": {
    "category": "DEPENDENCY_OUTAGE",
    "confidence": 0.82,
    "hypothesis": "..."
  },
  "auto_fixed": [
    {"action": "start_execution", "result": "success"}
  ],
  "needs_human": [
    {"reason": "code_regression", "action": "review_pr"}
  ],
  "tickets_created": [...],
  "prs_created": [...],
  "notifications_sent": [...]
}
```

**Coordinator Workflow** (common to all jobs):

```
1. Normalize event → internal job type
   ↓
2. Load context from DynamoDB Registry:
   - Workflow metadata (owners, SLA, outputs, criticality)
   - Safe-actions policy (what can be auto-fixed?)
   ↓
3. Select specialist(s) to run:
   - PIPELINE_FAILURE → Pipeline RCA Agent + Remediation Agent (if needed)
   - API_FAILURE → Runtime/API Agent + Code Fix Agent (if code regression)
   - DQ_CHECK → Data Quality Agent
   ↓
4. Set budgets:
   - max_cloudwatch_query_window (e.g., 30 minutes)
   - max_tool_calls (e.g., 20 calls per specialist)
   - max_auto_retries (e.g., 1 retry per incident)
   ↓
5. Execute specialists and collect structured JSON outputs:
   - Each specialist returns: InvestigationResult JSON
   - Coordinator tracks: tool calls, time spent, tokens used
   ↓
6. Resolve conflicts (if multiple specialists disagree):
   - Example: DQ says "bad data" but pipeline succeeded
   - Coordinator uses LLM to reconcile conflicting evidence
   ↓
7. Decide actions:
   - notify_only (read-only, just inform)
   - auto_remediate_tier1 (safe, low-risk actions)
   - open_pr (code changes)
   - escalate_to_incident (needs human review)
   ↓
8. Policy gate any write tool calls:
   - For each action: policy_engine.evaluate_action(action, context)
   - If denied: remove from action list, add to "needs_human"
   ↓
9. Execute approved actions (via Remediation Agent or direct MCP calls)
   ↓
10. Verify outcomes:
    - Check metrics recovered (error rate, latency)
    - Verify job state (SUCCEEDED)
    - Quick DQ check (if applicable)
   ↓
11. Publish notifications:
    - Slack: Human-readable summary
    - Jira: Ticket created (if escalation needed)
   ↓
12. Persist results:
    - S3: Evidence bundle (all MCP tool results, LLM outputs)
    - DynamoDB: Incident record (metadata, fingerprint, outcome)
    - DynamoDB: Fingerprint updates (for learning)
```

**Key Responsibilities**:
- **Budget management**: Prevent runaway tool calls, token usage
- **Conflict resolution**: When specialists disagree, coordinator reconciles
- **Policy enforcement**: All write actions must pass policy engine
- **Audit trail**: Log all decisions, tool calls, outcomes

---

### Specialist Agents: The Domain Experts

Specialist agents perform focused investigations in their domain. Each returns structured JSON output.

---

#### A. Pipeline RCA Agent (`agents/pipeline_rca_agent.py`)

**Trigger**: 
- Step Functions execution: `FAILED` | `TIMED_OUT` | `ABORTED`
- Glue job `FAILED`
- EMR step `FAILED`
- Late pipeline (from daily sweep)

**Workflow**:
1. **Identify failing execution**:
   - `orchestration-sfn`: `describe_execution(execution_arn)`
   - `orchestration-sfn`: `get_execution_history(execution_arn)` → identify failing state

2. **Map to underlying compute**:
   - Extract Glue job run ID or EMR cluster/step ID from execution history

3. **Pull compute details**:
   - `data-execution`: `get_glue_job_run(job_name, run_id)`
   - `data-execution`: `get_emr_step(cluster_id, step_id)`

4. **Pull evidence from logs**:
   - `data-execution`: `get_log_groups_for_job(job_name)`
   - `observability-cw`: `query_logs(error_patterns, time_window)`
   - `observability-cw`: `extract_error_fingerprints(logs)`

5. **Classify root cause** (LLM with structured prompt):
   - `DATA_LATE_MISSING` - Upstream data not arrived
   - `SCHEMA_DRIFT` - Schema changed
   - `DEPENDENCY_OUTAGE` - External service down
   - `OOM_TIMEOUT` - Resource exhaustion
   - `PERMISSIONS` - IAM/access issue
   - `CODE_REGRESSION` - Recent code change caused issue
   - `UNKNOWN` - Need more investigation

6. **Produce output**: `PipelineIncidentAnalysis` JSON
```json
{
  "classification": "DEPENDENCY_OUTAGE",
  "confidence": 0.82,
  "root_cause_hypothesis": "FastAPI service returned 503",
  "evidence_refs": ["s3://evidence/exec-123.json", "s3://evidence/logs-123.json"],
  "recommended_actions": ["restart_ecs_service", "rerun_pipeline"],
  "safe_to_autofix": true,
  "impact": {
    "downstream_workflows": ["workflow-b", "workflow-c"],
    "data_impact": "partition: 2024-01-15 missing"
  }
}
```

---

#### B. Remediation Agent (`agents/remediation_agent.py`)

**Trigger**: Coordinator receives analysis with `safe_to_autofix=true`

**Workflow**:
1. **Convert recommended actions → explicit tool calls**:
   - `rerun_pipeline` → `orchestration-sfn.start_execution(state_machine_arn, input)`
   - `restart_ecs_service` → `runtime-ecs.force_new_deployment(service_name)`

2. **Policy check each action**:
   - `policy_engine.evaluate_action(action, context)` for each action
   - Remove denied actions from execution plan

3. **Execute safe actions** (in order):
   - `orchestration-sfn`: `redrive_execution(execution_arn)` OR `start_execution(...)`
   - `data-execution`: `start_glue_job_run(job_name)`
   - `runtime-ecs`: `force_new_deployment(service_name)`

4. **Verify**:
   - Wait 30-60 seconds
   - Check job state: `RUNNING` → `SUCCEEDED`
   - Quick DQ check: Verify output partition exists (via Data Quality Agent)

5. **Handle failures**:
   - If unsuccessful after max retries: stop automation, escalate
   - If repeated failures (circuit breaker): disable auto-remediation for this workflow

**Output**: `RemediationResult` JSON
```json
{
  "actions_taken": [
    {"action": "start_execution", "result": "success", "execution_arn": "..."}
  ],
  "verification": {
    "status": "verified",
    "execution_state": "SUCCEEDED",
    "dq_check": "passed"
  },
  "rollback_needed": false
}
```

---

#### C. Runtime/API Incident Agent (`agents/api_incident_agent.py`)

**Trigger**: 
- CloudWatch alarm (5xx rate spike, latency p95 spike)
- Error signature spikes in logs
- Pipeline RCA says dependency outage due to API

**Workflow**:
1. **Service health check**:
   - `runtime-ecs`: `describe_service(service_name)`
   - `runtime-ecs`: `list_tasks(service_name)` → `describe_tasks(...)` → check stop reasons

2. **Collect evidence**:
   - `observability-cw`: `get_metric_timeseries(5xx_rate, latency_p99, cpu, mem)`
   - `observability-cw`: `query_logs(error_patterns)` → `extract_error_fingerprints`
   - `runtime-ecs`: `get_alb_target_health(service_name)`

3. **Classify issue** (LLM):
   - `DEPLOY_REGRESSION` - Recent deploy caused issue
   - `SATURATION` - Traffic spike overload
   - `CRASH_LOOP_OOM` - Tasks crashing, memory issues
   - `DEPENDENCY_OUTAGE` - Downstream service failure
   - `MISCONFIG` - Configuration error

4. **Recommend remediation**:
   - `restart_service` (force new deployment)
   - `temporary_scale_up` (increase desired count)
   - `rollback_deploy` (if deploy regression detected)

5. **Optional auto-actions** (Tier 1, policy-gated):
   - `runtime-ecs`: `force_new_deployment(service_name)`
   - `runtime-ecs`: `update_desired_count(service_name, new_count)` (within bounds)

6. **Verify**:
   - Error rate drops (< 0.1% for 5 minutes)
   - Latency returns to baseline (p95 < threshold)
   - No continued crash-loop

**Output**: `ApiIncidentAnalysis` JSON
```json
{
  "classification": "CRASH_LOOP_OOM",
  "confidence": 0.91,
  "root_cause": "Tasks OOM due to memory leak in recent deploy",
  "evidence_refs": [...],
  "recommended_actions": ["restart_service", "rollback_deploy"],
  "actions_taken": [{"action": "force_new_deployment", "result": "success"}],
  "verification": {"error_rate": 0.05, "status": "recovered"}
}
```

---

#### D. Data Quality Agent (`agents/data_quality_agent.py`)

**Trigger**: 
- After workflow success (post-processing check)
- Daily sweep (scheduled)
- Pipeline failure suspected due to data issues

**Workflow**:
1. **Determine target datasets**:
   - From Registry: Map workflow outputs to datasets + partition scheme

2. **Check freshness/partitions**:
   - `data-quality`: `get_latest_partition(dataset_id)`
   - Compare expected vs actual partition

3. **Run DQ ruleset**:
   - `data-quality`: `run_ruleset(dataset_id, ruleset_id, partitions)`
   - Execute Athena queries for:
     - Freshness (partition arrived on time?)
     - Volume (record count within expected range?)
     - Completeness (nulls, missing columns)
     - Uniqueness (duplicates)
     - Drift (statistical distribution changed?)

4. **Compare to baseline**:
   - `state/baselines.py`: Read 7-day / 28-day trends from DynamoDB
   - Identify deviations beyond threshold

5. **Output**: `DataQualityResult` JSON
```json
{
  "dataset_id": "raw.events",
  "partitions": ["2024-01-15"],
  "overall_status": "FAIL",
  "checks": [
    {
      "rule": "freshness",
      "status": "PASS",
      "expected": "2024-01-15 10:00",
      "actual": "2024-01-15 10:05"
    },
    {
      "rule": "volume",
      "status": "FAIL",
      "expected_range": [10000, 50000],
      "actual": 500,
      "severity": "CRITICAL"
    }
  ],
  "likely_cause": "bad_data_entering_lake",
  "impacted_downstream": ["pipeline-b", "pipeline-c"]
}
```

---

#### E. Code Fix Agent (`agents/code_fix_agent.py`)

**Trigger**: 
- Pipeline/API RCA classification = `CODE_REGRESSION`
- Recurring fingerprint with no infra/data explanation

**Workflow**:
1. **Create code search plan** from error fingerprint:
   - Extract: exception name, function names, endpoint path, table name

2. **Search and locate**:
   - `devtools-github`: `search_code(query, repository)`
   - Identify relevant files

3. **Read relevant code**:
   - `devtools-github`: `read_file(repository, file_path, ref)`
   - Check recent changes: `git_blame`, `recent_commits`

4. **Identify likely fix** (LLM):
   - Analyze code + error pattern
   - Propose fix (diff)
   - Suggest test cases

5. **Optional PR creation** (policy-gated):
   - `devtools-github`: `create_branch(repository, branch_name)`
   - `devtools-github`: `create_pr(repository, title, description, diff)`

6. **Notify**:
   - Share PR link + explanation
   - Include reproduction steps + rollout plan

**Output**: `BugFixProposal` JSON
```json
{
  "bug_location": {
    "repository": "data-platform/pipelines",
    "file": "transform.py",
    "line": 42,
    "function": "process_events"
  },
  "root_cause": "Null pointer exception when handling empty partitions",
  "proposed_fix": {
    "diff": "--- a/transform.py\n+++ b/transform.py\n...",
    "explanation": "Add null check before processing partition"
  },
  "test_cases": ["test_empty_partition", "test_null_handling"],
  "pr_created": true,
  "pr_url": "https://github.com/.../pull/123"
}
```

---

#### F. Cost & Capacity Agent (`agents/cost_agent.py`)

**Trigger**: 
- Daily scan (scheduled)
- Weekly deep review (scheduled)
- Cost anomaly alarm (optional)

**Workflow**:
1. **Pull cost signals**:
   - `finops`: `get_cost_by_service(time_range)`
   - `finops`: `get_cost_by_tag(time_range)`

2. **Identify waste patterns**:
   - `finops`: `detect_idle_resources()` (stopped but allocated)
   - `finops`: `ecs_rightsizing_recommendation(service_name)` (p95 CPU/mem analysis)
   - Pipeline cost hotspots: `finops.pipeline_cost_hotspots()` (rerun storms, long runtimes)

3. **Generate ranked recommendations** (LLM):
   - Calculate expected monthly savings
   - Assess risk (low/medium/high)
   - Identify quick wins

4. **Create tickets/PRs** (optional, policy-gated):
   - Infra repo PRs for rightsizing changes (not auto-applied in prod)
   - Create Jira tickets for manual review

**Output**: `CostOptimizationReport` JSON
```json
{
  "time_range": "2024-01-01 to 2024-01-31",
  "total_cost": 50000,
  "recommendations": [
    {
      "rank": 1,
      "type": "rightsize_ecs_service",
      "service": "data-api-prod",
      "current": {"cpu": 4096, "memory": 8192},
      "recommended": {"cpu": 2048, "memory": 4096},
      "monthly_savings": 500,
      "risk": "low",
      "steps": ["update_task_definition", "deploy", "monitor"]
    },
    {
      "rank": 2,
      "type": "fix_retry_storm",
      "workflow": "pipeline-etl-prod",
      "issue": "Failing repeatedly, causing 100+ reruns",
      "monthly_savings": 1000,
      "action": "fix_root_cause"
    }
  ],
  "total_potential_savings": 1500
}
```

---

#### G. Daily Sweep Agent (Orchestrated by Coordinator)

**Trigger**: Scheduled daily (and optionally hourly)

**Workflow**:
1. **Check workflow health** (fan-out):
   - Expected executions vs actual (for all 300+ workflows)
   - Detect failures, timeouts, SLA misses

2. **Run DQ for critical datasets**:
   - Execute Data Quality Agent for all critical tables

3. **Check API health signals**:
   - Runtime/API Agent quick health checks

4. **Cost quick scan**:
   - Cost Agent light analysis (not deep review)

5. **Produce daily digest**:
   - Summarize findings
   - Create incidents for any issues found
   - Generate digest message

**Output**: `DailyDigest` JSON
```json
{
  "date": "2024-01-15",
  "workflows_checked": 300,
  "issues_found": 5,
  "incidents_created": [
    {"type": "pipeline_failure", "count": 2},
    {"type": "dq_violation", "count": 1},
    {"type": "api_incident", "count": 2}
  ],
  "cost_anomalies": [],
  "summary": "5 issues detected, 3 auto-remediated"
}
```

---

### Workflow Mapping: Event Types → Agent Coordination

| Event Type | Coordinator Activates | Flow |
|-----------|----------------------|------|
| `PIPELINE_FAILURE` | Pipeline RCA Agent → Remediation Agent (if needed) → DQ quick check | Investigate → Fix → Verify |
| `API_FAILURE` | Runtime/API Agent → Code Fix Agent (if code regression) → Remediation Agent | Investigate → Fix → Verify |
| `DQ_CHECK_REQUEST` | Data Quality Agent | Check → Report violations |
| `COST_DAILY_SCAN` | Cost & Capacity Agent | Analyze → Generate recommendations |
| `DAILY_SWEEP` | Daily Sweep Agent (fan-out) | Check all → Digest |

**Example: Pipeline Failure Flow**:
```
Coordinator receives PIPELINE_FAILURE event
  ↓
Activates Pipeline RCA Agent
  - Gathers evidence via MCP tools
  - Classifies root cause (DEPENDENCY_OUTAGE)
  - Returns: safe_to_autofix=true
  ↓
Coordinator evaluates policy: auto_remediate? → allowed (nonprod)
  ↓
Activates Remediation Agent
  - Executes: start_execution(...)
  - Verifies: execution SUCCEEDED
  ↓
Coordinator activates Data Quality Agent (quick check)
  - Verifies output partition exists
  ↓
Coordinator merges outputs → Decision Packet
  ↓
Stores evidence, notifies team
```

---

#### Core Components Summary

```
agent-host/
├── main.py                    # Entrypoint: SQS polling loop (long-running)
├── dispatcher.py              # Routes events → workflows
├── config.py                  # Environment config (MCP URLs, AWS settings)
├── logging.py                 # Structured logging
│
├── workflows/                 # Workflow orchestrators
│   ├── pipeline_failure.py   # Step 1: Classify → Step 2: RCA → Step 3: Remediate
│   ├── api_failure.py        # ECS service failure workflow
│   ├── dq_check.py           # Data quality check workflow
│   ├── daily_sweep.py        # Proactive health check workflow
│   └── cost_daily_scan.py    # Cost optimization workflow
│
├── agents/                    # Specialist agents (LLM + tool orchestration)
│   ├── coordinator.py        # Multi-agent coordination
│   ├── pipeline_rca_agent.py # Pipeline failure investigation
│   ├── remediation_agent.py  # Fix plan + execution
│   ├── data_quality_agent.py # DQ violation analysis
│   ├── code_fix_agent.py     # Code change proposals
│   └── cost_agent.py         # Cost recommendations
│
├── mcp_client/                # MCP protocol clients
│   ├── base.py               # HTTP client (retries, timeouts)
│   ├── orchestration.py      # Step Functions MCP
│   ├── observability.py      # CloudWatch MCP
│   ├── data_execution.py     # Glue/EMR MCP
│   └── ...                   # Other MCP clients
│
├── policy/                    # Safety guardrails
│   ├── engine.py             # Policy evaluation
│   ├── tiers.py              # Tier definitions
│   └── rules/                # YAML rule files
│
├── state/                     # Memory / learning
│   ├── registry.py           # Workflow registry (DynamoDB)
│   ├── incident_store.py     # Incident history (DynamoDB)
│   ├── baselines.py          # Normal patterns (DynamoDB)
│   └── evidence_store.py     # Evidence packs (S3)
│
└── prompts/                   # LLM prompt templates
    ├── rca_prompt.md         # Structured RCA generation
    ├── plan_prompt.md        # Remediation plan generation
    └── pr_prompt.md          # PR generation
```

**Key Interfaces**:
```python
# Workflow interface
class Workflow:
    def handle(self, event: Event) -> WorkflowResult:
        """Orchestrates agent calls, collects evidence, produces result"""
        
# Agent interface  
class Agent:
    def investigate(self, context: Context) -> InvestigationResult:
        """Calls MCP tools, builds context, calls LLM, returns structured result"""
        
    def remediate(self, plan: RemediationPlan) -> RemediationResult:
        """Executes fix plan via MCP tools (policy-gated)"""

# MCP Client interface
class MCPClient:
    def call_tool(self, tool_name: str, args: dict) -> ToolResult:
        """HTTP call to MCP server, returns structured result"""
```

---

#### Agent Host Step-by-Step: Pipeline Failure Example

```
1. SQS message arrives: {"type": "PIPELINE_FAILURE", "execution_arn": "..."}
   ↓
2. main.py consumes message → dispatcher.py routes to pipeline_failure workflow
   ↓
3. Workflow activates pipeline_rca_agent
   ↓
4. Agent calls MCP tools (via mcp_client):
   - orchestration-sfn: get_execution_details(execution_arn)
   - orchestration-sfn: get_execution_history(execution_arn)
   - observability-cw: query_logs(error_patterns, time_range)
   - observability-cw: get_metrics(glue_job_metrics)
   ↓
5. Agent collects evidence → builds context object
   ↓
6. Agent calls LLM with structured prompt (prompts/rca_prompt.md)
   - Forces JSON output with: classification, root_cause, confidence, actions
   ↓
7. Policy engine evaluates: safe_to_autofix? (checks tier, allowlist)
   ↓
8. If allowed (nonprod): remediation_agent creates plan
   - Plan: {"action": "start_execution", "state_machine_arn": "..."}
   - Policy check: evaluate_action("start_execution", context) → allowed=True
   - Execute: mcp_client.orchestration.start_execution(...)
   ↓
9. Verification: Agent checks if execution started successfully
   ↓
10. Evidence stored:
    - S3: evidence/<incident_id>.json (logs, metrics, RCA packet)
    - DynamoDB: incident_record (metadata, fingerprint, outcome)
   ↓
11. Notification via chatops MCP (Slack/Jira) with summary
   ↓
12. Learning: Update baselines, store successful remediation pattern
```

This is the **agentic loop**: Detect → Diagnose → Act → Verify → Record → Learn

---

## Agent Workflows: The Playbooks

Workflows are the "playbooks" the Agent Host runs automatically when events/jobs arrive. Each workflow orchestrates multiple agents and MCP tools to complete an operational objective.

**Common Pattern**: `Detect → Collect Evidence → Decide → Act (optional) → Verify → Notify → Learn`

---

### 1. Pipeline Failure Workflow (`pipeline_failure.py`)

**Trigger**: 
- Step Functions execution fails (EventBridge → SQS)
- Glue/EMR job fails (EventBridge → SQS)

**Event Type**: `PIPELINE_FAILURE`

**Steps**:
1. **Identify failure context**
   - Extract execution ARN / job run ID from event
   - Fetch workflow metadata from registry (name, owner, tier)

2. **Gather evidence** (via MCP tools)
   - `orchestration-sfn`: Get execution details (status, cause, input/output)
   - `orchestration-sfn`: Get execution history (failing step, state transitions)
   - `data-execution`: Get Glue/EMR job run details (if applicable)
   - `observability-cw`: Query logs for error patterns (stack traces, error messages)
   - `observability-cw`: Get metrics (execution duration, resource usage)

3. **Root cause analysis** (Pipeline RCA Agent + LLM)
   - Classify failure type: `DATA_ISSUE` | `DEPENDENCY_OUTAGE` | `RESOURCE_LIMIT` | `PERMISSIONS` | `CODE_BUG`
   - Generate RCA packet with confidence score
   - Identify root cause with evidence links

4. **Remediation planning** (Remediation Agent)
   - Generate fix plan: `rerun_execution` | `fix_data` | `wait_for_dependency` | `escalate`
   - Check policy: Is auto-remediation allowed? (tier, allowlist, time window)

5. **Execute remediation** (if policy allows)
   - `orchestration-sfn`: Start new execution (redrive)
   - `data-execution`: Retry Glue job
   - Verification: Wait 30s, check execution status

6. **Store & notify**
   - Write evidence pack to S3
   - Record incident to DynamoDB (with fingerprint for learning)
   - `chatops`: Notify team via Slack/Jira with RCA summary

**Output**: **Incident Packet** (RCA + next steps + evidence)

**Components Used**:
- `agents/pipeline_rca_agent.py`
- `agents/remediation_agent.py`
- `mcp_client/orchestration.py`
- `mcp_client/data_execution.py`
- `mcp_client/observability.py`

---

### 2. Pipeline SLA / Late Data Workflow (`daily_sweep.py`)

**Trigger**: 
- Scheduled daily/hourly sweep (CloudWatch Events → SQS)
- Manual trigger for specific workflow

**Event Type**: `DAILY_SWEEP` or `PIPELINE_SLA_CHECK`

**Steps**:
1. **Identify expected executions**
   - Query registry for all active workflows (300+)
   - For each workflow: Check expected execution schedule
   - Compare expected vs actual executions in last window

2. **Detect anomalies**
   - Missing executions (should have run but didn't)
   - Late executions (running beyond SLA)
   - Stuck executions (running too long)

3. **Investigate causes** (if missing/late)
   - `orchestration-sfn`: List recent executions (check if upstream failed)
   - `observability-cw`: Query logs for dependency failures
   - Check if upstream workflow blocked this one

4. **Generate recommendations**
   - Identify root cause: upstream failure, schedule issue, resource constraint
   - Recommend actions: `backfill_execution` | `fix_upstream` | `adjust_schedule`
   - Calculate data impact: Which downstream workflows are affected?

5. **Notify & create tickets**
   - `chatops`: Alert owners of late/missing data
   - Create backfill plan if needed
   - Update registry: Mark workflow as "needs attention"

**Output**: **Late pipeline / Missing data alert** + backfill plan

**Components Used**:
- `state/registry.py` (workflow metadata)
- `mcp_client/orchestration.py`
- `agents/remediation_agent.py` (backfill planning)

---

### 3. Data Quality Workflow (`dq_check.py`)

**Trigger**: 
- After pipeline success (post-processing DQ check)
- Scheduled hourly/daily sweep (CloudWatch Events → SQS)
- Manual trigger for specific dataset

**Event Type**: `DQ_CHECK_REQUEST` or `DQ_SCHEDULED_CHECK`

**Steps**:
1. **Identify dataset to check**
   - Extract dataset/partition from event (or from pipeline completion event)
   - Load DQ ruleset from `data-quality/dq_rules/rulesets/`

2. **Run DQ validations** (Data Quality Agent + Athena)
   - `data-quality`: Execute Athena queries for:
     - Freshness (data arrived on time?)
     - Volume (record count within expected range?)
     - Completeness (nulls, missing columns)
     - Uniqueness (duplicates)
     - Drift (statistical distribution changed?)
   - Compare against baselines (7-day / 28-day trends)

3. **Evaluate results**
   - Calculate DQ score per rule
   - Identify violations: Which rules failed? What's the impact?

4. **Generate incident** (if violations found)
   - Classify severity: `CRITICAL` | `WARNING`
   - Identify impacted time window (which partitions are bad?)
   - Calculate downstream impact (which pipelines consume this data?)

5. **Recommend remediation** (Data Quality Agent)
   - Quarantine bad partitions
   - Backfill from source
   - Fix upstream pipeline (if data generation issue)

6. **Store & notify**
   - Store DQ scorecard to S3
   - Record violation incident to DynamoDB
   - `chatops`: Alert data owners with DQ report

**Output**: **DQ scorecard** + "Bad data entering lake" incident (if violations)

**Components Used**:
- `agents/data_quality_agent.py`
- `mcp_client/data_quality.py`
- `state/baselines.py` (trend comparison)

---

### 4. API Incident Workflow (`api_failure.py`)

**Trigger**: 
- CloudWatch alarm (5xx rate spike, latency spike)
- ECS service health check failure
- Error spike detected in logs

**Event Type**: `API_FAILURE`

**Steps**:
1. **Gather service context**
   - Extract ECS service name / cluster from alarm
   - `runtime-ecs`: Get service details (desired count, running tasks, recent deployments)

2. **Collect evidence** (API Incident Agent + MCP tools)
   - `runtime-ecs`: List tasks, check stop reasons (crashes, OOM)
   - `observability-cw`: Query logs for error patterns (5xx, exceptions, stack traces)
   - `observability-cw`: Get metrics (request rate, latency p99, error rate)
   - `runtime-ecs`: Check ALB target health

3. **Classify issue** (API Incident Agent + LLM)
   - Type: `DEPLOY_REGRESSION` | `OVERLOAD` | `DEPENDENCY_OUTAGE` | `CONFIG_ERROR` | `CODE_BUG`
   - Identify root cause: Recent deploy? Traffic spike? Downstream service failure?

4. **Generate remediation plan**
   - Actions: `restart_service` | `scale_up` | `rollback_deploy` | `fix_config`
   - Check policy: Is auto-remediation allowed? (prod vs nonprod)

5. **Execute remediation** (if policy allows)
   - `runtime-ecs`: Restart service (force new deployment)
   - `runtime-ecs`: Scale up tasks (temporary)
   - Verification: Wait 60s, check metrics recovered

6. **Store & notify**
   - Write evidence pack (logs, metrics, deploy history)
   - Record incident with correlation to pipeline failures (if applicable)
   - `chatops`: Alert on-call with incident summary

**Output**: **API incident summary** + actions taken

**Components Used**:
- `agents/api_incident_agent.py`
- `mcp_client/runtime.py`
- `mcp_client/observability.py`

---

### 5. Code Bug Analysis Workflow (integrated into `pipeline_failure.py` or `api_failure.py`)

**Trigger**: 
- RCA suggests "code bug likely" (pipeline or API failure)
- Manual investigation request

**Event Type**: Part of `PIPELINE_FAILURE` or `API_FAILURE` workflow

**Steps**:
1. **Locate code path**
   - Extract error fingerprint from logs (stack trace, error message)
   - Map to code repository + file path (via registry or log analysis)

2. **Investigate code** (Code Fix Agent + GitHub)
   - `devtools-github`: Read relevant files
   - `devtools-github`: Check recent changes (git blame, recent commits)
   - Identify likely bug: What changed recently? What's the code pattern?

3. **Generate fix proposal** (Code Fix Agent + LLM)
   - Propose code changes (diff)
   - Suggest test cases
   - Explain why this fixes the issue

4. **Create PR** (optional, policy-gated)
   - `devtools-github`: Create branch + PR with fix
   - Add description: Bug analysis, fix rationale, test plan
   - Request review from code owners

5. **Notify team**
   - `chatops`: Share PR link + explanation
   - Include rollout guidance (canary deploy? full deploy?)

**Output**: **PR / fix proposal** + explanation

**Components Used**:
- `agents/code_fix_agent.py`
- `mcp_client/devtools.py`

---

### 6. Cost Optimization Workflow (`cost_daily_scan.py`)

**Trigger**: 
- Daily scan (CloudWatch Events → SQS)
- Weekly deep review (scheduled)
- Manual trigger

**Event Type**: `COST_DAILY_SCAN` or `COST_WEEKLY_REVIEW`

**Steps**:
1. **Pull cost data** (Cost Agent + FinOps MCP)
   - `finops`: Query Cost Explorer (service/tag breakdown)
   - `finops`: Get utilization metrics (ECS tasks, Glue jobs, EMR clusters)

2. **Identify waste patterns**
   - Underutilized ECS services (low CPU/memory, but running 24/7)
   - Long-running Glue/EMR jobs (could be optimized)
   - Rerun/retry storms (same pipeline failing repeatedly, wasting compute)
   - Idle resources (stopped but allocated)

3. **Analyze opportunities** (Cost Agent + LLM)
   - Rank by savings potential: Highest impact first
   - Calculate estimated savings: $X/month if we rightsize service Y
   - Identify quick wins: What can we fix immediately?

4. **Generate recommendations**
   - Rightsizing: Downsize ECS service from 4GB → 2GB (save $X/month)
   - Schedule optimization: Run non-critical jobs at off-peak hours
   - Fix retry storms: Address root cause of repeated failures
   - Resource cleanup: Terminate idle EMR clusters

5. **Create action plan** (if policy allows)
   - `runtime-ecs`: Update ECS service task definition (rightsizing)
   - `data-execution`: Stop idle jobs/clusters
   - `orchestration-sfn`: Update schedule for cost optimization

6. **Store & notify**
   - Generate cost report (S3)
   - Create ticket for manual review (large changes)
   - `chatops`: Weekly cost summary + top recommendations

**Output**: **"Top cost savings opportunities" report**

**Components Used**:
- `agents/cost_agent.py`
- `mcp_client/finops.py`
- `mcp_client/runtime.py`

---

### Workflow Orchestration Pattern

All workflows follow this pattern:

```python
class Workflow:
    def handle(self, event: Event) -> WorkflowResult:
        # 1. Idempotency check
        incident_id = generate_incident_id(event)
        if incident_store.exists(incident_id):
            return WorkflowResult(skipped=True, reason="duplicate")
        
        # 2. Gather context
        context = self._build_context(event)
        
        # 3. Activate specialist agent(s)
        agent = self._select_agent(event.type)
        investigation = agent.investigate(context)
        
        # 4. Policy check
        if investigation.recommended_actions:
            decision = policy_engine.evaluate_action(
                action=investigation.recommended_actions[0],
                context=context
            )
            
            # 5. Execute remediation (if allowed)
            if decision.allowed:
                remediation_agent.execute(investigation.remediation_plan)
        
        # 6. Store evidence
        evidence_store.save(incident_id, investigation.evidence)
        incident_store.save(incident_id, investigation.rca_packet)
        
        # 7. Notify
        chatops.notify(investigation.summary)
        
        return WorkflowResult(success=True, incident_id=incident_id)
```

---

### Separation of Concerns: Agent Host vs MCP Servers

**✅ MCP Servers Should Be "Tool Adapters"**:
- Call AWS APIs (boto3 wrappers)
- Return structured results (typed responses)
- Enforce allowlists (security boundaries)
- Handle AWS errors gracefully
- No deep reasoning or business logic
- No LLM calls
- No state persistence (stateless)

**✅ Agent Host Should Contain**:
- Reasoning logic (LLM calls, decision-making)
- Multi-step workflows (orchestration)
- Policies and safety checks (guardrails)
- State persistence (DynamoDB, S3)
- Coordination and summarization (multi-agent)
- Learning from past incidents (fingerprints, patterns)

**Why This Matters**:
- **Security**: Agent Host doesn't need AWS credentials (MCP servers do)
- **Testability**: Mock MCP servers easily (just HTTP endpoints)
- **Maintainability**: Clear boundaries, no business logic in MCP servers
- **Scalability**: Scale Agent Host and MCP servers independently

**Example of What NOT to Do**:
```python
# ❌ BAD: MCP server doing reasoning
# mcp-servers/orchestration-sfn/app.py
@app.post("/tools/analyze_failure")
def analyze_failure(execution_arn: str):
    # DON'T: Call LLM here
    # DON'T: Do complex decision-making
    # DON'T: Store state
    pass

# ✅ GOOD: MCP server just returns data
# mcp-servers/orchestration-sfn/app.py
@app.post("/tools/get_execution_details")
def get_execution_details(execution_arn: str):
    # DO: Call boto3, return structured result
    result = boto3.client('stepfunctions').describe_execution(...)
    return {"result": result}
```

---

### MCP Servers (`mcp-servers/`)

**Pattern**: FastAPI app exposing MCP protocol over HTTP

**Common Structure**:
```
app.py          # FastAPI routes (/tools, /health)
schemas.py      # Pydantic models for requests/responses
aws_*.py        # boto3 wrappers (aws_sfn.py, aws_logs.py, etc.)
allowlist.py    # Resource allowlist validation
config.py       # Environment variables, settings
logging.py      # Structured logging
```

**MCP Protocol** (simplified):
```python
POST /tools
{
  "tool": "list_executions",
  "arguments": {
    "state_machine_arn": "...",
    "status_filter": "FAILED"
  }
}

Response:
{
  "result": [...],
  "evidence_refs": ["s3://bucket/evidence-123.json"]
}
```

**All MCP Servers**:
1. Validate allowlists (prevent cross-tenant access)
2. Use boto3 with error handling
3. Return structured, typed responses
4. Log all tool calls for audit
5. Support pagination for large result sets

---

### Shared Schemas (`shared/`)

**Purpose**: Type-safe event/evidence/RCA models shared across components

**Key Schemas**:
- `schemas/events.py`: Event types (PipelineFailure, APIFailure, DQCheck, etc.)
- `schemas/evidence.py`: Evidence pack structure (logs, metrics, traces)
- `schemas/rca.py`: RCA packet (root_cause, timeline, recommendations)
- `schemas/tools/*.py`: MCP tool request/response schemas

**Benefits**:
- Type safety across Agent Host and MCP servers
- Schema evolution without breaking changes
- Documentation via Pydantic models

---

## Critical Design Decisions

### 1. MCP vs Direct AWS SDK
**Decision**: Use MCP servers instead of direct boto3 in Agent Host

**Rationale**:
- Separation of concerns: Agent Host doesn't need AWS credentials
- Security: MCP servers enforce allowlists, least-privilege IAM
- Testability: MCP servers can be stubbed/mocked
- Multi-cloud future: Swap MCP implementation without changing Agent Host

**Trade-off**: Additional network hop, but acceptable for control plane

---

### 2. LLM Provider Choice
**Decision**: Support multiple providers (OpenAI, Anthropic, AWS Bedrock)

**Rationale**:
- Avoid vendor lock-in
- Cost optimization (use cheaper models where possible)
- Fallback if one provider is down

**Implementation**: LLM client abstraction in Agent Host, configurable per workflow

---

### 3. State Storage
**Decision**: DynamoDB for incidents/registry, S3 for evidence blobs

**Rationale**:
- DynamoDB: Fast lookups, TTL for incident cleanup
- S3: Cost-effective for large evidence packs, versioning
- Separation: Hot data (DynamoDB) vs cold data (S3)

---

### 4. Event Processing Model
**Decision**: SQS FIFO queues with at-least-once delivery

**Rationale**:
- FIFO: Process events in order (important for incident updates)
- At-least-once: Acceptable for idempotent operations
- Dead-letter queues: Handle poison messages

**Idempotency**: All workflows must handle duplicate events (check incident_store)

---

### 5. Policy Engine
**Decision**: YAML-based rules with Python evaluation engine

**Rationale**:
- Human-readable rules (not code)
- Version-controlled (Git)
- Can be updated without code deploy

**Structure**:
```yaml
# policy/rules/prod.yaml
tier: prod
rules:
  - action: start_execution
    allowed: false  # Never auto-remediate in prod
  - action: stop_execution
    allowed: true
    conditions:
      - cost_threshold > 1000  # Stop runaway costs
```

---

## Dependencies & Build Order

### 1. Foundation First
```
shared/schemas/          → No dependencies
  ↓
mcp-servers/base/        → Uses shared schemas
  ↓
agent-host/mcp_client/   → Uses shared schemas
agent-host/workflows/    → Uses shared schemas
  ↓
agent-host/dispatcher/   → Uses workflows
agent-host/main.py       → Uses dispatcher
```

### 2. MVP Critical Path
1. **shared/schemas** - Define Event, Evidence, RCA models
2. **mcp-servers/orchestration-sfn** - Step Functions tools
3. **mcp-servers/observability-cloudwatch** - Logs/metrics tools
4. **agent-host/mcp_client/base** - HTTP client for MCP
5. **agent-host/workflows/pipeline_failure** - First workflow
6. **agent-host/agents/pipeline_rca_agent** - First agent
7. **agent-host/dispatcher** - Route events
8. **agent-host/main** - Entrypoint

---

## Testing Strategy

### Unit Tests
- MCP servers: Mock boto3 calls
- Agent Host: Mock MCP clients, LLM responses
- Policy engine: Rule evaluation logic

### Integration Tests
- End-to-end: Sample event → RCA generation (local)
- MCP integration: Agent Host → MCP server → AWS (stubbed)

### Production Testing
- Shadow mode: Process events but don't write (policy: read-only)
- Gradual rollout: Enable auto-remediation in nonprod first
- A/B testing: Compare auto-remediation vs manual

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM cost explosion | Token limits, caching, use cheaper models for simple tasks |
| Accidental prod writes | Policy engine default deny, require explicit allowlist |
| MCP server failures | Retries, circuit breakers, fallback to manual process |
| Event backlog | Auto-scaling Agent Host, DLQ monitoring |
| False positives | Learning system, human feedback loop |

---

## Next Steps

1. **Review this plan** - Confirm priorities, adjust phases
2. **Start Phase 0 (MVP)**:
   - Implement shared schemas first
   - Build MCP orchestration-sfn (minimal: list_executions, get_execution)
   - Build agent-host workflow skeleton
   - Test with sample event locally
3. **Iterate** - MVP → Feedback → Refine → Next Phase

---

## Event-Driven vs Scheduled Workflows

### Event-Driven (Reactive)
**Trigger**: Real-time events via EventBridge → SQS
- `PIPELINE_FAILURE` - Step Functions/Glue execution fails
- `API_FAILURE` - ECS service returns 5xx or crashes
- `DQ_VIOLATION` - Data quality check fails (can be triggered by scheduled DQ checks)

**Processing**: Agent Host consumes from SQS immediately upon event arrival

### Scheduled (Proactive)
**Trigger**: CloudWatch Events (cron) → SQS
- `DAILY_SWEEP` - Daily health checks for all 300+ workflows
- `COST_WEEKLY_REVIEW` - Weekly cost analysis and recommendations
- `DQ_SCHEDULED_CHECK` - Hourly/daily data quality validations

**Processing**: Agent Host processes scheduled events same as event-driven (via SQS)

**Pattern**: Both use same Agent Host dispatcher and workflow system
```python
# dispatcher.py handles both
if event.type == "PIPELINE_FAILURE":
    return pipeline_failure_workflow
elif event.type == "DAILY_SWEEP":
    return daily_sweep_workflow
```

---

## Open Questions

1. **LLM Provider**: Which provider(s) to use initially? ✅ **RESOLVED**: Support all (Bedrock, OpenAI, Anthropic, Gemini) via abstraction layer. Default configurable via `LLM_PROVIDER` env var.
2. **Remediation scope**: Which actions auto-execute? (rerun? stop? scale?)
3. **Multi-tenant**: Do we need tenant isolation from day 1?
4. **Cost tracking**: What's the LLM budget per incident?
5. **Daily sweep scope**: Which checks run in daily sweep? (all 300 workflows? sample? tier-based?)

---

## Resources

- [MCP Protocol Spec](https://modelcontextprotocol.io) (reference)
- [AWS Step Functions Events](https://docs.aws.amazon.com/step-functions/latest/dg/cw-events.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
