# ops-autopilot 🚀

**ops-autopilot** is an **Agentic Operations + DataOps control plane** for AWS that uses an **AI Agent Host** and **domain-first MCP Servers** to monitor, investigate, and respond to production issues across:

- **AWS Step Functions** (workflow orchestration)
- **AWS Glue / EMR Spark** (data processing)
- **ECS Fargate FastAPI services** (runtime APIs / integrations)
- **CloudWatch Logs + Metrics** (observability + evidence collection)
- **Athena + Glue Data Catalog** (data quality validation)
- **GitHub** (code investigation + fix proposals / PR automation)
- **FinOps / Cost Optimization** (rightsizing + waste detection)

This platform enables a closed-loop operational workflow:

✅ **Detect → Collect Evidence → RCA → Plan → (Optional Auto-Fix) → Verify → Notify → Learn**

---

## Why this repo exists

Modern cloud environments run hundreds of workflows and services daily. Ops teams spend significant time on:

- monitoring pipelines and APIs
- investigating failures via logs/metrics
- identifying root causes
- rerunning jobs / recovering services
- validating data quality
- creating tickets and coordinating fixes
- proposing cost optimizations

This project aims to reduce that toil by building a production-ready **Agent Host + MCP server ecosystem**.

---

## Key components

### 1) AI Agent Host (Coordinator + Specialist agents)
The **Agent Host** is the "brain" of the system. It:
- consumes events from **SQS**
- routes them to the correct workflow
- calls MCP tools for evidence
- produces RCA packets and recommendations
- applies policy gates for write actions
- stores evidence + learns from previous incidents

Location: [`agent-host/`](./agent-host)

---

### 2) MCP Servers (domain-first tool adapters)
MCP servers provide the “hands” — safe, typed, auditable tool APIs.

- `mcp-orchestration` → Step Functions tools
- `mcp-observability` → CloudWatch logs/metrics tools
- `mcp-data-execution` → Glue + EMR tools
- `mcp-runtime` → ECS + ALB tools
- `mcp-data-quality` → Athena + Glue Catalog tools
- `mcp-finops` → cost signals + rightsizing recommendations
- `mcp-devtools` → GitHub tools
- `mcp-chatops` → Slack/Jira/PagerDuty integrations (optional)

Location: [`mcp-servers/`](./mcp-servers)

> MCP servers are intentionally “dumb adapters”. All agent reasoning happens in the Agent Host.

---

## MVP scope (first milestone)

The first “thin vertical slice” delivers immediate value:

✅ **Agent Host + PIPELINE_FAILURE workflow**  
✅ **mcp-orchestration (Step Functions)**  
✅ **mcp-observability (CloudWatch)**  
✅ Produces an **automatic RCA packet** for Step Functions execution failures.

---

## Architecture overview (high level)

**Inputs**
- Step Functions / Glue / EMR execution state events
- ECS alarms (5xx, latency, crash-loops)
- DQ checks (daily/hourly)
- daily sweeps + cost scans

**Event flow**
`EventBridge → SQS → Agent Host → MCP tool calls → RCA packet → ChatOps/Ticketing + Evidence store`

---

## Folder structure

ops-autopilot/
agent-host/ # Agent runtime + workflows (Coordinator + specialists)
mcp-servers/ # MCP servers grouped by domain
shared/ # Shared schemas/utilities
docs/ # Architecture, runbooks, skills.md packs, ADRs
infra/ # Terraform/CDK for AWS deployment
scripts/ # Local dev helpers
docker-compose.yml # Local dev stack


---

## Running locally (MVP)

### Prerequisites
- Python 3.11+
- Docker + docker-compose
- (Optional) AWS credentials with permissions to Step Functions + CloudWatch

### 

1) Start MCP servers
bash
docker-compose up --build

This should start:

mcp-orchestration on http://localhost:8001

mcp-observability on http://localhost:8002

2) Run the Agent Host in local mode

In another terminal:

cd agent-host
python -m agent_host.main --local-file ./src/agent_host/sample_events/pipeline_failure.json

Expected output

A readable incident summary printed in stdout

A structured RCA JSON saved under:

agent-host/evidence/<incident_id>.json

Environment variables
Agent Host
Variable	Description	Default
MCP_ORCHESTRATION_URL	URL of orchestration MCP server	http://localhost:8001
MCP_OBSERVABILITY_URL	URL of observability MCP server	http://localhost:8002
AWS_REGION	AWS region	us-east-1
DEFAULT_LOG_GROUPS	Comma-separated CW log group list	empty
SQS_QUEUE_URL	Queue URL (AWS mode)	unset
MCP servers (example)
Variable	Description
AWS_REGION	AWS region
ALLOWLIST_STATE_MACHINES	Allowed Step Function ARNs
ALLOWLIST_LOG_GROUPS	Allowed CloudWatch log groups
Production deployment (planned)

The production deployment runs the Agent Host and MCP servers on AWS:

ECS Fargate services

SQS queues (incidents, DQ, cost, daily)

EventBridge rules for execution/alarm events

DynamoDB tables for registry, incidents, baselines

S3 for evidence storage

IAM roles per MCP domain (least privilege)

See: docs/architecture/deployment.md

Safety model (important)

This platform supports autonomous actions, but defaults to read-only behavior until policies are enabled.

Write actions are:

explicitly separated

policy-gated

idempotent

verified after execution

audited

See: docs/architecture/policy-engine.md

Docs and skills

Architecture & design docs: docs/architecture/

AI coding skill packs: docs/skills/