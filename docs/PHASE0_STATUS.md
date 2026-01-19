# Phase 0 Status & Next Steps

**Last Updated**: Current session  
**Phase Goal**: End-to-end pipeline failure detection → RCA generation

---

## ✅ Completed Components

### 1. Shared Schemas (`shared/src/shared/schemas/`)
- ✅ `common.py` - Base types (Timestamp, IncidentID, ExecutionARN, etc.)
- ✅ `events.py` - All event types (PipelineFailure, APIFailure, DQCheck, etc.)
- ✅ `evidence.py` - Evidence pack structure (ExecutionDetails, LogEvidence, etc.)
- ✅ `rca.py` - RCA models (FailureClassification, PipelineIncidentAnalysis, etc.)

### 2. MCP Client Base (`agent-host/src/agent_host/mcp_client/`)
- ✅ `base.py` - HTTP client with:
  - Retry logic (exponential backoff)
  - Circuit breaker pattern (CLOSED, OPEN, HALF_OPEN)
  - Configurable timeouts
  - Error handling (MCPError, MCPConnectionError, etc.)
- ✅ `devtools.py` - GitHub MCP client wrapper

### 3. MCP Servers
- ✅ **orchestration-sfn** - Fully implemented
  - `list_executions`, `get_execution_details`, `get_execution_history`
  - `start_execution`, `stop_execution`
  - Multi-region support (auto-detects from ARNs)
  - Resource allowlist
  - README.md complete
- ✅ **devtools-github** - Fully implemented
  - `search_code`, `read_file`, `get_recent_commits`
  - `get_file_blame`, `create_branch`, `create_pr`
  - Repository allowlist
  - README.md complete

### 4. Agent Host Foundation
- ✅ `config.py` - Environment-aware configuration (local vs AWS)
- ✅ `dispatcher.py` - Event routing to workflows
- ✅ `logging.py` - Structured logging
- ✅ `main.py` - Entrypoint with SQS polling and local file mode
- ✅ `workflows/pipeline_failure.py` - Pipeline failure workflow
- ✅ `workflows/base.py` - Workflow base class
- ✅ `agents/pipeline_rca_agent.py` - Pipeline RCA agent with:
  - LLM integration (all providers)
  - GitHub code investigation
  - Evidence collection
  - Structured RCA generation
- ✅ `state/incident_store.py` - Incident storage (local + DynamoDB placeholder)
- ✅ `state/evidence_store.py` - Evidence storage (local + S3 placeholder)

### 5. LLM Integration (`agent-host/src/agent_host/llm/`)
- ✅ `base.py` - Abstract LLMClient interface
- ✅ `providers/openai.py` - OpenAI provider
- ✅ `providers/anthropic.py` - Anthropic Claude provider
- ✅ `providers/gemini.py` - Google Gemini provider
- ✅ `providers/grok.py` - xAI Grok provider
- ✅ `providers/bedrock.py` - AWS Bedrock provider
- ✅ `factory.py` - LLM factory for provider selection
- ✅ `prompts/rca_prompt.md` - RCA prompt template

### 6. Local Development Setup
- ✅ `docker-compose.yml` - Local MCP server orchestration
- ✅ Dockerfiles for MCP servers
- ✅ Sample event file (`pipeline_failure.json`)

---

## ⚠️ Remaining for Phase 0 MVP

### Priority 1: Critical MCP Servers

#### 1. Observability MCP Server (`mcp-servers/observability-cloudwatch/`)
**Status**: Files exist but need implementation

**Required Tools:**
- `query_logs` - Query CloudWatch Logs Insights
- `get_metrics` - Get CloudWatch metrics
- `extract_error_fingerprints` - Extract error patterns from logs

**Why Critical**: Pipeline RCA Agent needs logs and metrics for evidence collection

**Files to Implement:**
- `app.py` - FastAPI routes
- `aws_logs.py` - CloudWatch Logs boto3 wrapper
- `aws_metrics.py` - CloudWatch Metrics boto3 wrapper
- `schemas.py` - Request/response models
- `allowlist.py` - Log group allowlist
- `config.py` - Configuration

**Estimated Effort**: 2-3 hours

---

#### 2. Data Execution MCP Server (`mcp-servers/data-execution-glue-emr/`)
**Status**: Files exist but need implementation

**Required Tools:**
- `get_glue_job_run` - Get Glue job run details
- `get_emr_step` - Get EMR step details
- `get_log_groups_for_job` - Map jobs to log groups

**Why Critical**: Pipeline failures often involve Glue/EMR jobs

**Files to Implement:**
- `app.py` - FastAPI routes
- `aws_glue.py` - Glue boto3 wrapper
- `aws_emr.py` - EMR boto3 wrapper
- `schemas.py` - Request/response models
- `allowlist.py` - Job/cluster allowlist
- `config.py` - Configuration

**Estimated Effort**: 2-3 hours

---

### Priority 2: Policy Engine & Coordinator

#### 3. Policy Engine (`agent-host/src/agent_host/policy/`)
**Status**: Not yet created

**Required Features:**
- Rule evaluation (tier-based: prod vs nonprod)
- Action gating (allow/deny write actions)
- Policy configuration (YAML/JSON)

**Files to Create:**
- `engine.py` - Policy evaluation logic
- `rules.py` - Policy rule definitions
- `config.py` - Policy configuration loader

**Basic Rules Needed:**
- Nonprod: Allow auto-remediation
- Prod: Deny auto-remediation (require approval)
- Tier detection from resource tags/names

**Estimated Effort**: 2-3 hours

---

#### 4. Coordinator Agent (`agent-host/src/agent_host/agents/coordinator.py`)
**Status**: File exists but needs implementation

**Required Features:**
- Orchestrate specialist agents
- Apply policy engine
- Merge agent outputs
- Budget management (prevent runaway tool calls)

**Key Responsibilities:**
- Route investigations to appropriate agents
- Collect and merge evidence
- Apply policy before write actions
- Coordinate multi-agent workflows

**Estimated Effort**: 3-4 hours

---

### Priority 3: Remediation Agent

#### 5. Remediation Agent (`agent-host/src/agent_host/agents/remediation_agent.py`)
**Status**: File exists but needs implementation

**Required Features:**
- Execute remediation plans
- Policy-gated actions
- Verification of fixes
- Audit logging

**Basic Actions:**
- Restart failed executions
- Retry with different parameters
- Scale resources (nonprod only)

**Estimated Effort**: 2-3 hours

---

### Priority 4: Testing & Integration

#### 6. End-to-End Testing
**Status**: Not started

**Required:**
- Test pipeline failure workflow end-to-end
- Verify LLM RCA generation
- Test GitHub code investigation
- Test policy engine gating
- Test local and AWS modes

**Test Scenarios:**
1. Process sample `pipeline_failure.json` event
2. Verify evidence collection from MCP servers
3. Verify LLM generates structured RCA
4. Verify GitHub investigation when CODE_REGRESSION detected
5. Verify policy engine blocks prod writes

**Estimated Effort**: 2-3 hours

---

## 📋 Recommended Next Steps (In Order)

### Step 1: Implement Observability MCP Server
**Why First**: Pipeline RCA Agent needs logs/metrics for evidence

```bash
# Files to implement:
mcp-servers/observability-cloudwatch/src/observability_cloudwatch/
  - app.py (FastAPI routes)
  - aws_logs.py (CloudWatch Logs wrapper)
  - aws_metrics.py (CloudWatch Metrics wrapper)
  - schemas.py (Request/response models)
```

**Key Tools:**
- `query_logs(query, log_groups, time_range)` - CloudWatch Logs Insights
- `get_metrics(namespace, metric_name, dimensions, time_range)` - CloudWatch Metrics
- `extract_error_fingerprints(logs)` - Pattern extraction

---

### Step 2: Implement Data Execution MCP Server
**Why Second**: Pipeline failures often involve Glue/EMR jobs

```bash
# Files to implement:
mcp-servers/data-execution-glue-emr/src/data_execution/
  - app.py (FastAPI routes)
  - aws_glue.py (Glue wrapper)
  - aws_emr.py (EMR wrapper)
  - schemas.py (Request/response models)
```

**Key Tools:**
- `get_glue_job_run(job_name, run_id)` - Glue job details
- `get_emr_step(cluster_id, step_id)` - EMR step details
- `get_log_groups_for_job(job_name)` - Map job to log groups

---

### Step 3: Implement Policy Engine
**Why Third**: Needed before remediation actions

```bash
# Files to create:
agent-host/src/agent_host/policy/
  - __init__.py
  - engine.py (Policy evaluation)
  - rules.py (Rule definitions)
  - config.py (Policy loader)
```

**Basic Implementation:**
- Tier detection (prod vs nonprod)
- Action allow/deny logic
- Simple rule engine

---

### Step 4: Implement Coordinator Agent
**Why Fourth**: Orchestrates all agents

```bash
# File to implement:
agent-host/src/agent_host/agents/coordinator.py
```

**Key Features:**
- Agent selection and orchestration
- Policy application
- Output merging
- Budget management

---

### Step 5: Implement Remediation Agent
**Why Fifth**: Execute fixes (policy-gated)

```bash
# File to implement:
agent-host/src/agent_host/agents/remediation_agent.py
```

**Key Features:**
- Execute remediation plans
- Policy-gated actions
- Verification
- Audit logging

---

### Step 6: End-to-End Testing
**Why Last**: Verify everything works together

**Test Plan:**
1. Start MCP servers (docker-compose)
2. Process sample event
3. Verify evidence collection
4. Verify LLM RCA
5. Verify GitHub investigation
6. Verify policy gating

---

## 🎯 Phase 0 Success Criteria

- ✅ Can process a sample `pipeline_failure.json` event
- ✅ Coordinator activates Pipeline RCA Agent
- ✅ Agent collects evidence from MCP servers
- ✅ Generates structured RCA JSON with classification, root cause, confidence
- ✅ GitHub investigation works when CODE_REGRESSION detected
- ✅ Policy engine gates write actions (nonprod allows, prod denies)
- ✅ Prints human-readable summary

---

## 📊 Progress Summary

| Component | Status | Progress |
|-----------|--------|----------|
| Shared Schemas | ✅ Complete | 100% |
| MCP Client Base | ✅ Complete | 100% |
| Orchestration MCP | ✅ Complete | 100% |
| GitHub MCP | ✅ Complete | 100% |
| Observability MCP | ⚠️ Pending | 0% |
| Data Execution MCP | ⚠️ Pending | 0% |
| Pipeline RCA Agent | ✅ Complete | 100% |
| LLM Integration | ✅ Complete | 100% |
| Policy Engine | ⚠️ Pending | 0% |
| Coordinator Agent | ⚠️ Pending | 0% |
| Remediation Agent | ⚠️ Pending | 0% |
| End-to-End Testing | ⚠️ Pending | 0% |

**Overall Phase 0 Progress**: ~60% Complete

---

## 🚀 Quick Start: Next Task

**Immediate Next Step**: Implement Observability MCP Server

```bash
# 1. Create CloudWatch Logs wrapper
mcp-servers/observability-cloudwatch/src/observability_cloudwatch/aws_logs.py

# 2. Create CloudWatch Metrics wrapper
mcp-servers/observability-cloudwatch/src/observability_cloudwatch/aws_metrics.py

# 3. Implement FastAPI routes
mcp-servers/observability-cloudwatch/src/observability_cloudwatch/app.py

# 4. Add to docker-compose.yml
# 5. Test with curl
```

**Estimated Time**: 2-3 hours

---

## 📝 Notes

- All MCP servers follow the same pattern (see orchestration-sfn for reference)
- Policy engine can start simple (tier-based allow/deny)
- Coordinator can be basic initially (just route to Pipeline RCA Agent)
- Remediation Agent can start with read-only actions (no writes yet)

**Goal**: Get end-to-end flow working first, then add complexity.
