# Ops AutoPilot 🤖

**AI-Powered Operations Automation for AWS Data Pipelines**

An intelligent agentic system that monitors, analyzes, and automatically remediates failures in 300+ Glue/EMR PySpark pipelines orchestrated by Step Functions, with continuous data quality monitoring, automated root cause analysis, and policy-gated remediation.

---

## 🎯 Overview

Ops AutoPilot is a production-ready AI operations platform that combines:
- **Multi-Agent Architecture** - Specialized AI agents for different incident types
- **Model Context Protocol (MCP) Servers** - Secure, domain-specific tool interfaces
- **LLM-Powered Analysis** - Automated root cause analysis using multiple LLM providers
- **Policy Engine** - Safety guardrails for automated remediation
- **Full Observability** - CloudWatch integration for logs, metrics, and traces

**Current Status**: Phase 0 MVP ~90% Complete ✅

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Event Sources                         │
│  Step Functions | Glue/EMR | ECS APIs | CloudWatch      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Host (Orchestrator)                   │
│  • Coordinator Agent                                    │
│  • Pipeline RCA Agent                                   │
│  • Remediation Agent                                    │
│  • Policy Engine                                        │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ MCP Servers  │ │ MCP Servers  │ │ MCP Servers  │
│ Orchestration│ │ Observability │ │ Data Exec   │
│   (Step Fn)  │ │ (CloudWatch) │ │ (Glue/EMR)  │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Key Components

1. **Agent Host** - Central orchestrator that routes events to specialist agents
2. **MCP Servers** - Domain-specific tool servers (orchestration, observability, data execution, devtools)
3. **Coordinator Agent** - Orchestrates specialist agents and applies policy
4. **Pipeline RCA Agent** - Investigates failures and generates root cause analysis
5. **Remediation Agent** - Executes policy-gated remediation actions
6. **Policy Engine** - Safety guardrails (tier-based, rate limiting, allowlists)

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

- **Decision Packet Storage**
  - Local file storage for development
  - Idempotency support
  - Full audit trail

### 🚧 Coming Soon (Phase 1+)

- AWS deployment (ECS Fargate, DynamoDB, S3)
- Data Quality Agent
- Cost Optimization Agent
- API Incident Agent
- Code Fix Agent

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and docker-compose
- AWS credentials configured (`~/.aws/credentials`)
- LLM API key (OpenAI, Anthropic, or AWS Bedrock access)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ops-autopilot
   ```

2. **Start MCP Servers**
   ```bash
   docker-compose up -d
   
   # Verify they're running
   curl http://localhost:8001/health  # orchestration-sfn
   curl http://localhost:8002/health  # observability-cloudwatch
   curl http://localhost:8003/health  # data-execution-glue-emr
   curl http://localhost:8007/health  # devtools-github
   ```

3. **Configure Environment**
   ```bash
   export LLM_PROVIDER=openai  # or anthropic, gemini, bedrock, grok
   export LLM_API_KEY=your-api-key
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx  # For code investigation
   export DEFAULT_REPOSITORY=owner/repo
   export AWS_REGION=us-east-1
   ```

4. **Process a Sample Event**
   ```bash
   cd agent-host
   python -m agent_host.main --local-file src/agent_host/sample_events/pipeline_failure.json
   ```

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

**MCP Server URLs** (auto-detected in local mode)
- Local: `http://localhost:8001`, `8002`, `8003`, `8007`
- AWS: Auto-discovered via service discovery

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

```bash
# From project root
cd agent-host
pytest tests/

# Run specific test
pytest tests/test_policy_engine.py
```

### Test End-to-End Flow

```bash
# Start MCP servers
docker-compose up -d

# Process sample event
python -m agent_host.main --local-file src/agent_host/sample_events/pipeline_failure.json

# Verify decision packet was saved
ls -la ./evidence/*_decision.json
```

---

## 📚 Documentation

- **[Current Status](docs/CURRENT_STATUS.md)** - Implementation progress
- **[High-Level Architecture Diagram](docs/architecture/ARCHITECTURE_DIAGRAM.md)** - Complete system architecture
- **[Code Flow & Process Lineage](docs/CODE_FLOW.md)** - Complete code-level flow documentation
- **[Architecture Overview](docs/architecture/overview.md)** - System design
- **[Implementation Plan](docs/implementation-plan.md)** - Detailed roadmap
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Local and AWS deployment
- **[MCP Servers](mcp-servers/README.md)** - MCP server documentation
- **[Policy Engine](agent-host/src/agent_host/policy/README.md)** - Policy rules guide

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
- [ ] End-to-end testing

### Phase 1: Production Hardening
- [ ] AWS deployment (ECS, DynamoDB, S3)
- [ ] Data Quality Agent
- [ ] Cost Optimization Agent
- [ ] Monitoring & alerting
- [ ] Terraform infrastructure

### Phase 2: Advanced Features
- [ ] API Incident Agent
- [ ] Code Fix Agent
- [ ] Multi-region support
- [ ] Advanced analytics

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
