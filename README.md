# Ops AutoPilot 🤖

**AI-Powered Operations Automation for AWS Data Pipelines**

An intelligent agentic system that monitors, analyzes, and automatically remediates failures in 300+ Glue/EMR PySpark pipelines orchestrated by Step Functions, with continuous data quality monitoring, automated root cause analysis, and policy-gated remediation.

---

## 🎯 Overview

Ops AutoPilot is a production-ready AI operations platform that combines:
- **Multi-Region Architecture** - Agent Host and MCP Servers deployed across multiple AWS regions for low latency and high availability
- **Multi-Agent Architecture** - Specialized AI agents for different incident types
- **Model Context Protocol (MCP) Servers** - Secure, domain-specific tool interfaces
- **LLM-Powered Analysis** - Automated root cause analysis using multiple LLM providers
- **Policy Engine** - Safety guardrails for automated remediation
- **Full Observability** - CloudWatch integration for logs, metrics, and traces
- **Global State Management** - DynamoDB Global Tables and Central S3 for unified incident tracking

**Current Status**: Phase 0 MVP ~90% Complete ✅  
**Deployment**: Supports both single-region and multi-region deployments

---

## 🏗️ Architecture

### Multi-Region Deployment Architecture

Ops AutoPilot is designed for **multi-region deployment**, with Agent Host and MCP Servers running in each operational region, while maintaining global state through DynamoDB Global Tables and a central S3 evidence bucket.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GLOBAL RESOURCES (Single Region)                          │
│                                                                              │
│  ┌──────────────────┐              ┌──────────────────┐                    │
│  │ DynamoDB Global  │              │ S3 Evidence      │                    │
│  │ Tables           │              │ Bucket (Central)  │                    │
│  │                  │              │                  │                    │
│  │ • workflow_      │              │ • evidence/      │                    │
│  │   registry       │              │   {region}/      │                    │
│  │ • incidents      │              │   {incident_id}/ │                    │
│  │ • baselines      │              │                  │                    │
│  │                  │              │ Replicated to    │                    │
│  │ Replicated to    │              │ all regions      │                    │
│  │ all regions      │              │                  │                    │
│  └──────────────────┘              └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│              REGIONAL DEPLOYMENTS (Per Operational Region)                    │
│                                                                              │
│  Region: us-east-1          Region: us-west-2          Region: eu-west-1   │
│  ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐│
│  │ Event Sources    │       │ Event Sources    │       │ Event Sources    ││
│  │ (Regional)       │       │ (Regional)       │       │ (Regional)       ││
│  └────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘│
│           │                          │                          │          │
│           ▼                          ▼                          ▼          │
│  ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐│
│  │ Agent Host       │       │ Agent Host       │       │ Agent Host       ││
│  │ (ECS Fargate)    │       │ (ECS Fargate)    │       │ (ECS Fargate)    ││
│  │                  │       │                  │       │                  ││
│  │ • Coordinator    │       │ • Coordinator    │       │ • Coordinator    ││
│  │ • Pipeline RCA  │       │ • Pipeline RCA  │       │ • Pipeline RCA  ││
│  │ • Remediation   │       │ • Remediation   │       │ • Remediation   ││
│  │ • Policy Engine │       │ • Policy Engine │       │ • Policy Engine ││
│  └────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘│
│           │                          │                          │          │
│           ▼                          ▼                          ▼          │
│  ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐│
│  │ MCP Servers      │       │ MCP Servers      │       │ MCP Servers      ││
│  │ (8 servers)      │       │ (8 servers)      │       │ (8 servers)      ││
│  │                  │       │                  │       │                  ││
│  │ • orchestration  │       │ • orchestration  │       │ • orchestration  ││
│  │ • observability  │       │ • observability  │       │ • observability  ││
│  │ • data-execution │       │ • data-execution │       │ • data-execution ││
│  │ • devtools       │       │ • devtools       │       │ • devtools       │
│  │ • ... (4 more)   │       │ • ... (4 more)   │       │ • ... (4 more)   ││
│  └──────────────────┘       └──────────────────┘       └──────────────────┘│
│           │                          │                          │          │
│           └──────────────────────────┴──────────────────────────┘          │
│                                    │                                         │
│                                    ▼                                         │
│                    ┌───────────────────────────────┐                        │
│                    │   AWS Services (Regional)     │                        │
│                    │   Step Functions, Glue, EMR   │                        │
│                    └───────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Agent Host** (Per Region) - Central orchestrator that routes events to specialist agents
   - Processes regional events with low latency
   - Accesses global DynamoDB tables for state
   - Writes evidence to central S3 bucket

2. **MCP Servers** (Per Region) - Domain-specific tool servers
   - Deployed in each operational region
   - Access regional AWS resources (Step Functions, CloudWatch, Glue, EMR)
   - Support multi-region operations via ARN extraction

3. **Global State** (Single Deployment)
   - **DynamoDB Global Tables** - Replicated across all regions for low-latency access
   - **Central S3 Bucket** - Single evidence store with regional prefixes

4. **Coordinator Agent** - Orchestrates specialist agents and applies policy
5. **Pipeline RCA Agent** - Investigates failures and generates root cause analysis
6. **Remediation Agent** - Executes policy-gated remediation actions
7. **Policy Engine** - Safety guardrails (tier-based, rate limiting, allowlists)

### Multi-Region Benefits

- ✅ **Low Latency** - Process incidents in the same region as failures
- ✅ **High Availability** - Regional failover if one region fails
- ✅ **Global State** - Single source of truth via DynamoDB Global Tables
- ✅ **Centralized Evidence** - All evidence in one S3 bucket for analysis
- ✅ **Regional Compliance** - Process data in required regions (GDPR, etc.)
- ✅ **Scalability** - Scale independently per region

### Deployment Options

**Single-Region Deployment** (Simpler, for development/testing):
- Agent Host and MCP Servers in one region
- Regional DynamoDB tables and S3 bucket
- Use `infra/terraform/main.tf`

**Multi-Region Deployment** (Production, recommended):
- Agent Host and MCP Servers in each operational region
- Global DynamoDB tables (replicated across regions)
- Central S3 evidence bucket (accessible from all regions)
- Use `infra/terraform/multi-region/` modules

**Local Development**:
- MCP Servers in Docker containers
- Agent Host runs locally
- Local file storage for evidence
- Use `docker-compose.yml` and `make local-run`

---

## ✨ Features

### ✅ Implemented (Phase 0)

- **Pipeline Failure Detection & Analysis**
  - Automatic evidence collection from Step Functions, Glue, EMR
  - LLM-powered root cause analysis with structured output
  - GitHub code investigation for CODE_REGRESSION incidents
  - Human-readable incident summaries

- **Policy-Gated Remediation**
  - Tier-based evaluation (prod vs nonprod)
  - Rate limiting and time window restrictions
  - Allowlist/deny list support
  - Automatic remediation for safe actions

- **MCP Server Architecture**
  - Orchestration (Step Functions) - 5 tools
  - Observability (CloudWatch) - 5 tools
  - Data Execution (Glue/EMR) - 7 tools
  - DevTools (GitHub) - 6 tools

- **Multi-LLM Support**
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude 3)
  - Google Gemini
  - AWS Bedrock
  - Grok (X.AI)

- **Multi-Region Deployment**
  - Agent Host and MCP Servers deployed per region
  - DynamoDB Global Tables for unified state
  - Central S3 evidence bucket with regional organization
  - Automatic region detection from ARNs

- **Decision Packet Storage**
  - Local file storage for development
  - DynamoDB Global Tables for production (multi-region)
  - S3 evidence storage (central bucket)
  - Idempotency support
  - Full audit trail

### 🚧 Coming Soon (Phase 1+)

- Data Quality Agent
- Cost Optimization Agent
- API Incident Agent
- Code Fix Agent
- Advanced monitoring & alerting

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and docker-compose
- AWS credentials configured (`~/.aws/credentials`)
- LLM API key (OpenAI, Anthropic, or AWS Bedrock access)
- Terraform (for AWS deployment)

### Local Development Setup

**Using Makefile (Recommended)**:
```bash
# Quick start - install dependencies and start MCP servers
make quick-start

# Run Agent Host with sample event
make local-run

# Or use custom event file
make local-run EVENT_FILE=path/to/event.json
```

**Manual Setup**:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ops-autopilot
   ```

2. **Install dependencies**
   ```bash
   make install
   # Or manually:
   pip install -e shared/
   pip install -e agent-host/
   ```

3. **Start MCP Servers**
   ```bash
   make docker-up
   # Or manually:
   docker-compose up -d
   
   # Verify they're running
   make docker-health
   ```

4. **Configure Environment**
   ```bash
   export LLM_PROVIDER=openai  # or anthropic, gemini, bedrock, grok
   export LLM_API_KEY=your-api-key
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx  # For code investigation
   export DEFAULT_REPOSITORY=owner/repo
   export AWS_REGION=us-east-1
   ```

5. **Process a Sample Event**
   ```bash
   make local-run
   # Or manually:
   cd agent-host
   python -m agent_host.main --local-file src/agent_host/sample_events/pipeline_failure.json
   ```

### AWS Deployment

#### Single-Region Deployment

```bash
cd infra/terraform
terraform init
terraform plan -var="environment=prod" -var="aws_region=us-east-1"
terraform apply
```

#### Multi-Region Deployment

**Step 1: Deploy Global Resources** (once, in primary region)
```bash
cd infra/terraform/multi-region/global
terraform init
terraform apply \
  -var="environment=prod" \
  -var="primary_region=us-east-1" \
  -var="replica_regions=['us-west-2','eu-west-1']"
```

**Step 2: Deploy Regional Resources** (per region)
```bash
cd infra/terraform/multi-region/regional
terraform workspace new us-east-1
terraform workspace select us-east-1
terraform apply \
  -var="aws_region=us-east-1" \
  -var="environment=prod" \
  -var="global_dynamodb_tables.workflow_registry=..." \
  -var="global_s3_evidence_bucket=..."
```

**Repeat Step 2 for each operational region** (us-west-2, eu-west-1, etc.)

See [Multi-Region Deployment Guide](docs/architecture/MULTI_REGION_DEPLOYMENT.md) for detailed instructions.

### Expected Output

You'll see a comprehensive human-readable summary:
```
╔══════════════════════════════════════════════════════════════════╗
║                    INCIDENT SUMMARY                              ║
╚══════════════════════════════════════════════════════════════════╝

Incident ID: incident_run-123456_20240115103000
Event Type: PIPELINE_FAILURE
Timestamp: 2024-01-15 10:30:00 UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT HAPPENED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline execution timed out after 300 seconds...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROOT CAUSE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classification: INFRASTRUCTURE_ISSUE
Confidence: HIGH (85%)
...
```

---

## 📁 Project Structure

```
ops-autopilot/
├── agent-host/              # Agent Host application
│   ├── src/agent_host/
│   │   ├── agents/          # Specialist agents
│   │   │   ├── coordinator.py
│   │   │   ├── pipeline_rca_agent.py
│   │   │   └── remediation_agent.py
│   │   ├── workflows/       # Event workflows
│   │   ├── policy/          # Policy engine
│   │   ├── mcp_client/      # MCP client wrappers
│   │   └── utils/           # Utilities
│   └── tests/
│
├── mcp-servers/             # MCP server implementations
│   ├── orchestration-sfn/   # Step Functions operations
│   ├── observability-cloudwatch/  # CloudWatch Logs/Metrics
│   ├── data-execution-glue-emr/   # Glue/EMR operations
│   └── devtools-github/     # GitHub operations
│
├── shared/                  # Shared schemas and types
│   └── src/shared/schemas/
│       ├── events.py        # Event type definitions
│       ├── evidence.py      # Evidence pack structure
│       └── rca.py           # RCA models
│
├── docs/                    # Documentation
│   ├── architecture/       # Architecture docs
│   ├── CURRENT_STATUS.md   # Current implementation status
│   └── implementation-plan.md
│
├── infra/                   # Infrastructure as Code
│   └── terraform/           # Terraform modules
│
└── docker-compose.yml       # Local development setup
```

---

## 🔧 Configuration

### Environment Variables

**LLM Configuration**
```bash
LLM_PROVIDER=openai|anthropic|gemini|bedrock|grok
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4  # Optional, uses provider default if not set
```

**GitHub (for code investigation)**
```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
DEFAULT_REPOSITORY=owner/repo
```

**AWS**
```bash
AWS_REGION=us-east-1
# Uses ~/.aws/credentials for authentication
```

**MCP Server URLs** (auto-detected based on environment)
- Local: `http://localhost:8001`, `8002`, `8003`, `8007`
- AWS (Single-Region): Auto-discovered via service discovery
- AWS (Multi-Region): Regional service discovery per region

**Multi-Region Configuration** (AWS Production)
```bash
# Global resources (set once)
DYNAMODB_PRIMARY_REGION=us-east-1
S3_EVIDENCE_REGION=us-east-1
DYNAMODB_REGISTRY=prod-ops-autopilot-workflow-registry
DYNAMODB_INCIDENTS=prod-ops-autopilot-incidents
S3_EVIDENCE_BUCKET=prod-ops-autopilot-evidence

# Regional resources (per region)
AWS_REGION=us-west-2  # Current region
SQS_QUEUE_INCIDENTS=https://sqs.us-west-2.amazonaws.com/.../incidents
```

---

## 📊 MCP Servers

| Server | Port | Tools | Description |
|--------|------|-------|-------------|
| orchestration-sfn | 8001 | 5 | Step Functions operations |
| observability-cloudwatch | 8002 | 5 | CloudWatch Logs & Metrics |
| data-execution-glue-emr | 8003 | 7 | Glue & EMR operations |
| devtools-github | 8007 | 6 | GitHub code operations |

Each MCP server:
- Exposes REST API with `/tools` endpoint
- Implements resource allowlists for security
- Supports health checks at `/health`
- Fully containerized with Docker

See `mcp-servers/README.md` for detailed documentation.

---

## 🧪 Testing

### Run Tests

**Using Makefile**:
```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests (requires MCP servers)
make test-coverage     # Tests with coverage report
```

**Manual**:
```bash
cd agent-host
pytest tests/

# Run specific test
pytest tests/test_policy_engine.py
```

### Test End-to-End Flow

```bash
# Start MCP servers
make docker-up

# Process sample event
make local-run

# Verify decision packet was saved
ls -la ./evidence/*_decision.json
```

---

## 📚 Documentation

- **[Current Status](docs/CURRENT_STATUS.md)** - Implementation progress
- **[High-Level Architecture Diagram](docs/architecture/ARCHITECTURE_DIAGRAM.md)** - Complete system architecture
- **[Multi-Region Deployment](docs/architecture/MULTI_REGION_DEPLOYMENT.md)** - Multi-region architecture and deployment guide
- **[Code Flow & Process Lineage](docs/CODE_FLOW.md)** - Complete code-level flow documentation
- **[Architecture Overview](docs/architecture/overview.md)** - System design
- **[Implementation Plan](docs/implementation-plan.md)** - Detailed roadmap
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Local and AWS deployment
- **[MCP Servers](mcp-servers/README.md)** - MCP server documentation
- **[Policy Engine](agent-host/src/agent_host/policy/README.md)** - Policy rules guide
- **[Terraform Structure](infra/terraform/STRUCTURE.md)** - Infrastructure code organization

---

## 🛡️ Security

- **Resource Allowlists** - All MCP servers enforce allowlists
- **Policy Engine** - Tier-based access control (prod vs nonprod)
- **Rate Limiting** - Prevents runaway automation
- **IAM Integration** - Least-privilege AWS access (Phase 1)
- **No Hardcoded Secrets** - All credentials via environment variables

---

## 🤝 Contributing

1. Check [CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for what's in progress
2. Review [implementation-plan.md](docs/implementation-plan.md) for roadmap
3. Follow existing code patterns and architecture
4. Add tests for new features
5. Update documentation

---

## 📈 Roadmap

### Phase 0: MVP (Current) ✅ ~90% Complete
- [x] Core agent architecture
- [x] Pipeline failure detection & RCA
- [x] Policy engine
- [x] MCP servers (4 complete)
- [x] Human-readable summaries
- [x] Decision packet storage
- [x] Multi-region deployment architecture
- [x] DynamoDB Global Tables support
- [x] Central S3 evidence bucket
- [ ] End-to-end testing

### Phase 1: Production Hardening
- [x] AWS deployment (ECS, DynamoDB, S3)
- [x] Multi-region Terraform modules
- [ ] Data Quality Agent
- [ ] Cost Optimization Agent
- [ ] Monitoring & alerting
- [ ] Production deployment validation

### Phase 2: Advanced Features
- [ ] API Incident Agent
- [ ] Code Fix Agent
- [ ] Advanced analytics
- [ ] Cross-region incident correlation
- [ ] Regional failover automation

---

## 📝 License

See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - MCP server framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [boto3](https://boto3.amazonaws.com/) - AWS SDK
- Multiple LLM providers (OpenAI, Anthropic, Google, AWS)

---

## 📞 Support

For questions or issues:
1. Check [CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for known issues
2. Review [implementation-plan.md](docs/implementation-plan.md) for architecture
3. See [docs/](docs/) for detailed documentation

---

**Status**: Phase 0 MVP ~90% Complete - Ready for End-to-End Testing 🚀  
**Deployment**: Multi-region ready - Deploy Agent Host and MCP Servers across all operational regions with global state management
