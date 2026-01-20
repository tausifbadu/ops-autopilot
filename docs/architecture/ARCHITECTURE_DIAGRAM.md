# Ops AutoPilot - High-Level Architecture Diagram

**Complete system architecture overview with component relationships and data flows**

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           EVENT SOURCES & INGESTION                                 │
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Step         │  │ AWS Glue     │  │ AWS EMR      │  │ ECS Services │         │
│  │ Functions    │  │ Jobs         │  │ Clusters     │  │ (APIs)        │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                 │                 │                   │
│         └──────────────────┴─────────────────┴─────────────────┘                   │
│                                    │                                               │
│                                    ▼                                               │
│                          ┌─────────────────────┐                                  │
│                          │   EventBridge        │                                  │
│                          │   (Event Routing)    │                                  │
│                          └──────────┬──────────┘                                  │
│                                     │                                               │
│                                     ▼                                               │
│                          ┌─────────────────────┐                                  │
│                          │   SQS Queues        │                                  │
│                          │  ┌──────────────┐  │                                  │
│                          │  │ incidents     │  │                                  │
│                          │  │ dq_checks     │  │                                  │
│                          │  │ cost_scan     │  │                                  │
│                          │  │ daily_sweep   │  │                                  │
│                          │  └──────────────┘  │                                  │
│                          └──────────┬──────────┘                                  │
└─────────────────────────────────────┼─────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           AGENT HOST (ECS Fargate)                                  │
│                    Long-Running Orchestration Service                               │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          MAIN ENTRY POINT                                    │  │
│  │  main.py                                                                     │  │
│  │  • SQS Polling Loop                                                          │  │
│  │  • Local File Processing                                                      │  │
│  └───────────────────────┬──────────────────────────────────────────────────────┘  │
│                           │                                                          │
│                           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          DISPATCHER                                           │  │
│  │  dispatcher.py                                                                │  │
│  │  • Routes events to workflows                                                 │  │
│  │  • Event type → Workflow mapping                                              │  │
│  └───────────────────────┬──────────────────────────────────────────────────────┘  │
│                           │                                                          │
│                           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          WORKFLOWS                                            │  │
│  │  workflows/                                                                    │  │
│  │  • pipeline_failure.py                                                        │  │
│  │  • api_failure.py                                                             │  │
│  │  • dq_check.py                                                                │  │
│  │  • cost_daily_scan.py                                                         │  │
│  │  • daily_sweep.py                                                             │  │
│  └───────────────────────┬──────────────────────────────────────────────────────┘  │
│                           │                                                          │
│                           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          COORDINATOR AGENT                                    │  │
│  │  agents/coordinator.py                                                        │  │
│  │  • Orchestrates specialist agents                                            │  │
│  │  • Applies policy engine                                                      │  │
│  │  • Merges outputs into DecisionPacket                                         │  │
│  │  • Budget management                                                           │  │
│  └───────────┬───────────────────────┬───────────────────────┬──────────────────┘  │
│              │                       │                       │                      │
│              ▼                       ▼                       ▼                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐            │
│  │ SPECIALIST       │   │ POLICY ENGINE    │   │ REMEDIATION      │            │
│  │ AGENTS           │   │ policy/engine.py  │   │ AGENT            │            │
│  │                  │   │                  │   │ agents/          │            │
│  │ • Pipeline RCA   │   │ • Tier detection │   │ remediation_     │            │
│  │ • API Incident   │   │ • Rule eval      │   │ agent.py         │            │
│  │ • Data Quality   │   │ • Rate limiting  │   │                  │            │
│  │ • Cost           │   │ • Allowlists     │   │ • Execute actions│            │
│  │ • Code Fix       │   │ • Time windows   │   │ • Verify results │            │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘            │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          LLM INTEGRATION                                      │  │
│  │  llm/                                                                        │  │
│  │  • Factory pattern (OpenAI, Anthropic, Gemini, Grok, Bedrock)              │  │
│  │  • Structured JSON outputs                                                   │  │
│  │  • Prompt templates                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          MCP CLIENT LIBRARY                                    │  │
│  │  mcp_client/                                                                  │  │
│  │  • base.py - HTTP client with circuit breakers, retries                     │  │
│  │  • orchestration.py - Step Functions client                                   │  │
│  │  • observability.py - CloudWatch client                                      │  │
│  │  • data_execution.py - Glue/EMR client                                       │  │
│  │  • devtools.py - GitHub client                                               │  │
│  └───────────────────────┬──────────────────────────────────────────────────────┘  │
│                           │                                                          │
│                           │ HTTP/JSON (MCP Protocol)                                 │
│                           │                                                          │
└───────────────────────────┼─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MCP SERVERS (ECS Fargate)                                 │
│                    Stateless Tool Adapters (FastAPI)                                │
│                                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Orchestration    │  │ Observability    │  │ Data Execution    │                │
│  │ orchestration-  │  │ observability-   │  │ data-execution-   │                │
│  │ sfn              │  │ cloudwatch       │  │ glue-emr          │                │
│  │                  │  │                  │  │                   │                │
│  │ • get_execution_ │  │ • query_logs     │  │ • get_glue_job_  │                │
│  │   details        │  │ • get_log_events │  │   run             │                │
│  │ • start_execution│  │ • get_metrics    │  │ • get_emr_step    │                │
│  │ • stop_execution │  │ • list_metrics   │  │ • get_log_groups_ │                │
│  │ • list_executions│  │ • extract_error_ │  │   for_job         │                │
│  │ • get_execution_ │  │   fingerprints   │  │ • get_emr_cluster │                │
│  │   history        │  │                  │  │                   │                │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                      │                           │
│           └─────────────────────┴──────────────────────┘                           │
│                           │                                                          │
│                           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          DevTools                                            │  │
│  │  devtools-github                                                             │  │
│  │                                                                              │  │
│  │  • search_code                                                               │  │
│  │  • read_file                                                                 │  │
│  │  • get_recent_commits                                                        │  │
│  │  • get_file_blame                                                            │  │
│  │  • create_branch                                                             │  │
│  │  • create_pr                                                                 │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          SECURITY LAYER                                       │  │
│  │  • Resource Allowlists (per MCP server)                                      │  │
│  │  • IAM Roles (least privilege)                                               │  │
│  │  • Policy Engine (tier-based gating)                                         │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────────────────────────┘
                            │
                            │ AWS SDK (boto3)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           AWS SERVICES                                               │
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Step         │  │ CloudWatch   │  │ AWS Glue     │  │ AWS EMR      │         │
│  │ Functions    │  │ Logs/Metrics │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ DynamoDB     │  │ S3           │  │ EventBridge  │  │ SQS          │         │
│  │ (State)      │  │ (Evidence)   │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                            │
                            │ External APIs
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                         │
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ GitHub API   │  │ LLM Providers │  │ LLM Providers│  │ LLM Providers│         │
│  │              │  │ OpenAI       │  │ Anthropic    │  │ Google       │         │
│  │              │  │ GPT-4/3.5    │  │ Claude 3     │  │ Gemini       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐                                               │
│  │ AWS Bedrock  │  │ xAI Grok     │                                               │
│  │ (Claude,     │  │              │                                               │
│  │  Llama, etc) │  │              │                                               │
│  └──────────────┘  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Interaction Flow

### Complete Event Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: EVENT INGESTION                                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Step Functions Execution Fails
    │
    ▼
EventBridge Rule (state = FAILED)
    │
    ▼
SQS Queue (incidents.fifo)
    │
    ▼
Agent Host (SQS Polling)
    │
    ▼
Dispatcher::dispatch(event)
    │
    ▼
PipelineFailureWorkflow::handle(event)


┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: INVESTIGATION                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

CoordinatorAgent::coordinate(event)
    │
    ├─→ PipelineRCAAgent::investigate(event)
    │   │
    │   ├─→ _gather_evidence()
    │   │   │
    │   │   ├─→ MCP Client → Orchestration MCP Server
    │   │   │   └─→ AWS Step Functions API
    │   │   │       └─→ get_execution_details()
    │   │   │
    │   │   └─→ MCP Client → Observability MCP Server
    │   │       └─→ AWS CloudWatch API
    │   │           └─→ query_logs(), get_metrics()
    │   │
    │   ├─→ _generate_rca()
    │   │   │
    │   │   └─→ LLM Provider (OpenAI/Claude/Gemini)
    │   │       └─→ Structured JSON RCA
    │   │
    │   └─→ _investigate_code_bug() [if CODE_REGRESSION]
    │       │
    │       └─→ MCP Client → GitHub MCP Server
    │           └─→ GitHub API
    │               └─→ search_code(), get_recent_commits()
    │
    └─→ PolicyEngine::evaluate_action()
        │
        └─→ Load YAML rules → Evaluate tier, rate limits, allowlists


┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: DECISION & REMEDIATION                                            │
└─────────────────────────────────────────────────────────────────────────────┘

DecisionPacket Created
    │
    ├─→ safe_to_autofix = True?
    │   │
    │   └─→ YES → RemediationAgent::execute_remediation(plan)
    │       │
    │       ├─→ Policy Re-Check (safety)
    │       │
    │       ├─→ MCP Client → Orchestration MCP Server
    │       │   └─→ AWS Step Functions API
    │       │       └─→ start_execution() / stop_execution()
    │       │
    │       └─→ _verify_remediation()
    │           └─→ Check execution status
    │
    └─→ NO → Escalate to Human (needs_human list)


┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: STORAGE & OUTPUT                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

IncidentStore::save_decision_packet()
    │
    ├─→ Local Mode: Save to ./evidence/
    │   └─→ {incident_id}_decision.json
    │
    └─→ AWS Mode: Save to DynamoDB + S3
        ├─→ DynamoDB: Decision packet metadata
        └─→ S3: Evidence bundles

format_decision_summary()
    │
    └─→ Print human-readable summary
```

---

## 🔄 Data Flow Architecture

### State Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STATE STORES                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   DynamoDB       │         │   S3 Bucket      │         │   Local Files    │
│   (Hot State)    │         │   (Cold Evidence) │         │   (Dev Mode)     │
│                  │         │                  │         │                  │
│ • Incidents      │         │ • Evidence Packs │         │ • ./evidence/    │
│ • Decision       │         │ • Log Bundles    │         │   {id}.json      │
│   Packets        │         │ • Daily Digests  │         │   {id}_decision. │
│ • Baselines      │         │ • RCA Reports    │         │   json            │
│ • Registry       │         │                  │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
```

### MCP Communication Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MCP PROTOCOL (HTTP/JSON)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Agent Host (MCP Client)
    │
    │ POST /tools
    │ {
    │   "tool": "get_execution_details",
    │   "arguments": {"execution_arn": "..."}
    │ }
    │
    ▼
MCP Server (FastAPI)
    │
    │ 1. Validate request
    │ 2. Check allowlist
    │ 3. Call AWS API (boto3)
    │ 4. Format response
    │
    ▼
Response
    │
    │ {
    │   "result": {...},
    │   "error": null
    │ }
    │
    ▼
Agent Host (Processes result)
```

---

## 🏛️ Deployment Architecture

### AWS Infrastructure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AWS VPC                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    ECS CLUSTER (Fargate)                                    │
│                                                                             │
│  ┌──────────────────────┐         ┌──────────────────────┐                │
│  │ Agent Host Service   │         │ MCP Server Services  │                │
│  │                      │         │                      │                │
│  │ • 1-3 Tasks          │         │ • orchestration-sfn  │                │
│  │ • Long-running       │         │ • observability-cw   │                │
│  │ • SQS Polling        │         │ • data-execution    │                │
│  │ • Stateful           │         │ • devtools-github    │                │
│  │                      │         │ • Stateless          │                │
│  │ Task Role:           │         │ • Auto-scaling        │                │
│  │ - SQS Read           │         │                      │                │
│  │ - DynamoDB Write     │         │ Task Roles:          │                │
│  │ - S3 Write           │         │ - Step Functions     │                │
│  │ - MCP Server Access  │         │ - CloudWatch         │                │
│  └──────────────────────┘         │ - Glue/EMR          │                │
│                                    │ - GitHub API        │                │
│                                    └──────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPPORTING SERVICES                                      │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ SQS Queues   │  │ DynamoDB     │  │ S3 Buckets   │  │ EventBridge  │ │
│  │              │  │ Tables        │  │              │  │ Rules        │ │
│  │ • incidents  │  │ • incidents  │  │ • evidence   │  │              │ │
│  │ • dq_checks  │  │ • registry    │  │ • digests    │  │              │ │
│  │ • cost_scan  │  │ • baselines   │  │              │  │              │ │
│  │ • daily_sweep│  │              │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Local Development Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT (Docker Compose)                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    Docker Compose Services                                   │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │ orchestration-sfn│  │ observability-cw  │  │ data-execution   │         │
│  │ Port: 8001      │  │ Port: 8002        │  │ Port: 8003      │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                             │
│  ┌──────────────────┐                                                       │
│  │ devtools-github  │                                                       │
│  │ Port: 8007      │                                                       │
│  └──────────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Agent Host (Python Process)
    │
    ├─→ Reads from local files (sample_events/)
    ├─→ Connects to MCP servers via localhost:8001, 8002, 8003, 8007
    ├─→ Saves evidence to ./evidence/ directory
    └─→ Uses AWS credentials from ~/.aws/credentials
```

---

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY LAYERS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Layer 1: Resource Allowlists (MCP Servers)
    │
    │ Each MCP server maintains allowlist of resources it can access
    │ • orchestration-sfn: State machine ARNs
    │ • observability-cw: Log group names
    │ • data-execution: Glue job names, EMR cluster IDs
    │ • devtools-github: Repository names
    │
    ▼

Layer 2: IAM Roles (AWS)
    │
    │ Least-privilege IAM roles per service
    │ • Agent Host: SQS, DynamoDB, S3, MCP server access
    │ • MCP Servers: Specific AWS service permissions
    │
    ▼

Layer 3: Policy Engine (Agent Host)
    │
    │ Tier-based policy evaluation
    │ • PROD: Default deny, explicit allow
    │ • NONPROD: Default allow, explicit deny (deletes)
    │ • Rate limiting
    │ • Time window restrictions
    │
    ▼

Layer 4: Circuit Breakers (MCP Client)
    │
    │ Prevents cascading failures
    │ • CLOSED: Normal operation
    │ • OPEN: Reject requests (service failing)
    │ • HALF_OPEN: Test recovery
```

---

## 📈 Scalability Architecture

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCALING STRATEGY                                         │
└─────────────────────────────────────────────────────────────────────────────┘

Agent Host
    │
    ├─→ Multiple ECS Tasks (1 per queue type)
    │   • Task 1: incidents queue
    │   • Task 2: dq_checks queue
    │   • Task 3: cost_scan queue
    │   • Task 4: daily_sweep queue
    │
    └─→ Auto-scaling based on SQS queue depth

MCP Servers
    │
    ├─→ Stateless design enables horizontal scaling
    ├─→ Auto-scaling based on:
    │   • CPU utilization
    │   • Request rate
    │   • Response time
    │
    └─→ Load balanced via ALB (optional) or direct service discovery
```

---

## 🔌 Integration Points

### External API Integrations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   GitHub API     │         │   LLM Providers │         │   AWS Services   │
│                  │         │                  │         │                  │
│ • Code Search    │         │ • OpenAI         │         │ • Step Functions │
│ • File Read      │         │ • Anthropic      │         │ • CloudWatch     │
│ • Commits        │         │ • Google Gemini  │         │ • Glue           │
│ • PR Creation    │         │ • AWS Bedrock    │         │ • EMR            │
│                  │         │ • xAI Grok       │         │ • DynamoDB       │
│ Rate Limited     │         │                  │         │ • S3             │
│ (GitHub)         │         │ API Keys/        │         │ • SQS            │
│                  │         │ IAM Roles        │         │ • EventBridge    │
└──────────────────┘         └──────────────────┘         └──────────────────┘
```

---

## 📦 Component Summary

### Agent Host Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **Main** | Entry point, SQS polling | `main.py` |
| **Dispatcher** | Event routing | `dispatcher.py` |
| **Workflows** | Event-specific handlers | `workflows/*.py` |
| **Coordinator** | Multi-agent orchestration | `agents/coordinator.py` |
| **Pipeline RCA** | Root cause analysis | `agents/pipeline_rca_agent.py` |
| **Remediation** | Action execution | `agents/remediation_agent.py` |
| **Policy Engine** | Safety guardrails | `policy/engine.py` |
| **MCP Client** | MCP server communication | `mcp_client/*.py` |
| **LLM Integration** | Multi-provider LLM | `llm/*.py` |
| **State Stores** | Incident/evidence storage | `state/*.py` |

### MCP Servers

| Server | Port | Tools | AWS Services |
|--------|------|-------|--------------|
| **orchestration-sfn** | 8001 | 5 | Step Functions |
| **observability-cloudwatch** | 8002 | 5 | CloudWatch Logs/Metrics |
| **data-execution-glue-emr** | 8003 | 7 | Glue, EMR |
| **devtools-github** | 8007 | 6 | GitHub API |

---

## 🎯 Key Design Principles

1. **Separation of Concerns**
   - MCP Servers = Dumb adapters (no business logic)
   - Agent Host = All reasoning (LLM, workflows, decisions)

2. **Stateless MCP Servers**
   - Can scale horizontally
   - No shared state between requests

3. **Stateful Agent Host**
   - Long-running process
   - Maintains workflow state
   - Enables multi-step reasoning

4. **Policy-Gated Actions**
   - All write actions require policy approval
   - Tier-based evaluation (prod vs nonprod)
   - Rate limiting and time windows

5. **Evidence-Based Decisions**
   - All decisions backed by collected evidence
   - Structured data (Pydantic models)
   - Full audit trail

6. **Resilience**
   - Circuit breakers for MCP calls
   - Retry logic with exponential backoff
   - Fallback to rule-based classification

---

## 📝 Notes

- **Agent Host** is a long-running ECS Fargate service (not Lambda)
- **MCP Servers** are stateless FastAPI services
- **Communication** between Agent Host and MCP Servers is via HTTP/JSON (MCP protocol)
- **State** is stored in DynamoDB (hot) and S3 (cold evidence)
- **Local Development** uses Docker Compose for MCP servers
- **Production** uses ECS Fargate for all services

---

**Last Updated**: Current Session  
**Version**: Phase 0 MVP Architecture
