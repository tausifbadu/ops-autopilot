# Multi-Region Deployment Architecture

**Scaling Ops AutoPilot across multiple AWS regions with global state management**

---

## 🎯 Multi-Region Strategy

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GLOBAL RESOURCES (Single Region)                        │
│                                                                             │
│  ┌──────────────────┐         ┌──────────────────┐                        │
│  │ DynamoDB Global  │         │ S3 Evidence      │                        │
│  │ Tables           │         │ Bucket (Central) │                        │
│  │                  │         │                  │                        │
│  │ • workflow_      │         │ • evidence/      │                        │
│  │   registry       │         │   {region}/      │                        │
│  │ • incidents      │         │   {incident_id}/ │                        │
│  │ • baselines      │         │                  │                        │
│  │                  │         │ Replicated to    │                        │
│  │ Replicated to    │         │ all regions via  │                        │
│  │ all regions      │         │ cross-region     │                        │
│  │                  │         │ replication      │                        │
│  └──────────────────┘         └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    REGIONAL RESOURCES (Per Region)                          │
│                                                                             │
│  Region: us-east-1          Region: us-west-2          Region: eu-west-1   │
│  ┌──────────────────┐       ┌──────────────────┐     ┌──────────────────┐│
│  │ ECS Cluster      │       │ ECS Cluster       │     │ ECS Cluster      ││
│  │                  │       │                   │     │                  ││
│  │ • Agent Host     │       │ • Agent Host      │     │ • Agent Host     ││
│  │ • MCP Servers    │       │ • MCP Servers     │     │ • MCP Servers    ││
│  │                  │       │                   │     │                  ││
│  │ SQS Queues       │       │ SQS Queues        │     │ SQS Queues       ││
│  │ • incidents      │       │ • incidents       │     │ • incidents     ││
│  │ • dq_checks      │       │ • dq_checks       │     │ • dq_checks      ││
│  │ • cost_scan      │       │ • cost_scan       │     │ • cost_scan      ││
│  │ • daily_sweep    │       │ • daily_sweep     │     │ • daily_sweep    ││
│  │                  │       │                   │     │                  ││
│  │ EventBridge      │       │ EventBridge       │     │ EventBridge      ││
│  │ Rules            │       │ Rules             │     │ Rules            ││
│  │                  │       │                   │     │                  ││
│  │ VPC              │       │ VPC               │     │ VPC              ││
│  │ ECR Repos        │       │ ECR Repos         │     │ ECR Repos        ││
│  └──────────────────┘       └──────────────────┘     └──────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Plan

### 1. Global Resources (Deploy Once)

**Location**: Primary region (e.g., `us-east-1`)

- **DynamoDB Global Tables**
  - `workflow_registry` - Global table with replication
  - `incidents` - Global table with replication
  - `baselines` - Global table with replication

- **S3 Evidence Bucket**
  - Single bucket in primary region
  - Cross-region replication enabled (optional)
  - Regional prefixes: `evidence/{region}/{incident_id}/`

### 2. Regional Resources (Deploy Per Region)

**Deploy in each operational region**:
- `us-east-1`, `us-west-2`, `eu-west-1`, `ap-southeast-1`, etc.

**Per Region**:
- ECS Cluster
- Agent Host service
- MCP Server services (all 8 servers)
- SQS Queues (regional)
- EventBridge Rules (regional)
- VPC and networking
- ECR Repositories (or use single ECR with cross-region replication)

### 3. Configuration Strategy

**Agent Host Configuration**:
- `DYNAMODB_REGION` - Primary region for global tables
- `S3_EVIDENCE_BUCKET` - Central bucket name
- `S3_EVIDENCE_REGION` - Primary region for S3
- `AWS_REGION` - Current region (for regional resources)
- `MCP_SERVER_URLS` - Regional MCP server endpoints

**MCP Server Configuration**:
- `AWS_REGION` - Current region (for regional AWS API calls)
- Multi-region support already implemented (extracts region from ARNs)

---

## 🔧 Terraform Implementation

### Directory Structure

```
infra/terraform/
├── main.tf                    # Single-region deployment (legacy)
├── multi-region/
│   ├── global/
│   │   ├── main.tf            # Global resources (DynamoDB, S3)
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── regional/
│   │   ├── main.tf            # Regional resources (ECS, SQS, etc.)
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── README.md              # Multi-region deployment guide
└── modules/
    └── ... (existing modules)
```

---

## 🚀 Deployment Steps

### Step 1: Deploy Global Resources

```bash
cd infra/terraform/multi-region/global
terraform init
terraform plan -var="primary_region=us-east-1"
terraform apply
```

**Outputs**:
- DynamoDB table names
- S3 bucket name
- Primary region

### Step 2: Deploy Regional Resources

**For each region**:
```bash
cd infra/terraform/multi-region/regional
terraform init
terraform workspace new us-east-1  # or us-west-2, eu-west-1, etc.
terraform plan \
  -var="aws_region=us-east-1" \
  -var="dynamodb_primary_region=us-east-1" \
  -var="s3_evidence_bucket=prod-ops-autopilot-evidence" \
  -var="s3_evidence_region=us-east-1"
terraform apply
```

**Repeat for each operational region**.

---

## 🔐 IAM Permissions

### Agent Host IAM Role (Per Region)

**Regional Permissions**:
- SQS: Read from regional queues
- ECS: Service discovery (for MCP servers)
- CloudWatch: Write logs

**Global Permissions**:
- DynamoDB: Read/Write to global tables (all regions)
- S3: Read/Write to central evidence bucket (cross-region)

### MCP Server IAM Roles (Per Region)

**Regional Permissions**:
- Step Functions: Regional access
- CloudWatch: Regional access
- Glue/EMR: Regional access
- ECS: Regional access

**Note**: MCP servers already support multi-region via ARN extraction.

---

## 📊 Data Flow

### Incident Processing Flow

```
Region: us-west-2
    │
    ├─→ Step Functions execution fails
    │
    ├─→ EventBridge rule (us-west-2)
    │
    ├─→ SQS queue (us-west-2/incidents)
    │
    ├─→ Agent Host (us-west-2)
    │   │
    │   ├─→ Reads from DynamoDB Global Table (any region)
    │   ├─→ Writes to DynamoDB Global Table (replicates to all regions)
    │   ├─→ Writes evidence to S3 (central bucket, us-east-1)
    │   │   └─→ Path: evidence/us-west-2/{incident_id}/
    │   │
    │   └─→ Calls MCP Servers (us-west-2, regional)
    │       └─→ MCP servers call AWS APIs (us-west-2)
    │
    └─→ Decision packet stored in DynamoDB (replicates globally)
```

### Evidence Storage Pattern

```
S3 Bucket: prod-ops-autopilot-evidence
│
├── evidence/
│   ├── us-east-1/
│   │   ├── incident_abc123/
│   │   │   ├── execution_details.json
│   │   │   ├── logs.json
│   │   │   └── rca.json
│   │   └── incident_def456/
│   │
│   ├── us-west-2/
│   │   ├── incident_ghi789/
│   │   └── ...
│   │
│   └── eu-west-1/
│       └── ...
```

---

## ⚙️ Configuration Updates

### Agent Host Config

```python
# agent-host/src/agent_host/config.py

class Config:
    # Regional settings
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Global resources
    dynamodb_primary_region: str = os.getenv("DYNAMODB_PRIMARY_REGION", "us-east-1")
    s3_evidence_bucket: str = os.getenv("S3_EVIDENCE_BUCKET", "prod-ops-autopilot-evidence")
    s3_evidence_region: str = os.getenv("S3_EVIDENCE_REGION", "us-east-1")
    
    # DynamoDB table names (same across all regions)
    dynamodb_registry: str = os.getenv("DYNAMODB_REGISTRY", "prod-ops-autopilot-workflow-registry")
    dynamodb_incidents: str = os.getenv("DYNAMODB_INCIDENTS", "prod-ops-autopilot-incidents")
    
    # Regional SQS queues
    sqs_queue_incidents: str = os.getenv("SQS_QUEUE_INCIDENTS", "...")
```

### DynamoDB Client (Global Tables)

```python
# Use primary region for DynamoDB client
dynamodb_client = boto3.client(
    "dynamodb",
    region_name=config.dynamodb_primary_region
)

# Global tables automatically replicate to all regions
# Reads can happen from any region (lower latency)
# Writes go to primary region (or any region with global tables)
```

### S3 Client (Central Bucket)

```python
# Use primary region for S3 client
s3_client = boto3.client(
    "s3",
    region_name=config.s3_evidence_region
)

# Store with regional prefix
s3_key = f"evidence/{config.aws_region}/{incident_id}/{filename}"
```

---

## 🔄 Replication & Consistency

### DynamoDB Global Tables

- **Automatic Replication**: Changes replicate to all regions within seconds
- **Eventual Consistency**: Reads from any region (may see slightly stale data)
- **Conflict Resolution**: Last-write-wins (standard DynamoDB behavior)

### S3 Evidence Bucket

- **Single Bucket**: All regions write to same bucket
- **Regional Prefixes**: Organized by region for easier management
- **Cross-Region Replication** (Optional): Can enable S3 cross-region replication for disaster recovery

---

## 📈 Benefits

1. **Low Latency**: Process incidents in the same region as failures
2. **High Availability**: If one region fails, others continue operating
3. **Global State**: Single source of truth for incidents and baselines
4. **Centralized Evidence**: All evidence in one place for analysis
5. **Regional Compliance**: Process data in required regions (GDPR, etc.)

---

## ⚠️ Considerations

1. **Cost**: Multiple ECS clusters and services per region
2. **Complexity**: More infrastructure to manage
3. **Eventual Consistency**: DynamoDB global tables have eventual consistency
4. **S3 Latency**: Writing to central S3 from remote regions (minimal impact)
5. **IAM Complexity**: Need to grant cross-region access to global resources

---

## 🎯 Next Steps

1. Create `infra/terraform/multi-region/` directory structure
2. Implement global DynamoDB tables module
3. Implement central S3 bucket module
4. Update regional deployment to reference global resources
5. Update Agent Host config to support global resources
6. Test deployment in 2-3 regions
7. Document operational procedures

---

**Last Updated**: Current Session  
**Status**: Design Phase
