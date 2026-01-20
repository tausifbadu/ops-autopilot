# Terraform Infrastructure Structure

**Explanation of the directory structure and why we have both `modules/` and `multi-region/`**

---

## 📁 Directory Structure

```
infra/terraform/
├── main.tf                    # Single-region deployment (legacy/original)
├── variables.tf               # Variables for single-region
├── outputs.tf                 # Outputs for single-region
│
├── modules/                   # 🔧 REUSABLE MODULES (Building Blocks)
│   ├── ecs-service/          # ECS Fargate service module
│   ├── dynamodb/             # DynamoDB table module
│   ├── s3/                   # S3 bucket module
│   ├── sqs/                  # SQS queue module
│   ├── iam/                  # IAM roles module
│   ├── vpc/                  # VPC module
│   ├── ecr/                  # ECR repository module
│   ├── alb/                  # ALB module
│   └── eventbridge/          # EventBridge rules module
│
└── multi-region/             # 🌍 MULTI-REGION DEPLOYMENTS (Uses Modules)
    ├── global/               # Global resources (deploy once)
    │   ├── main.tf           # DynamoDB Global Tables + Central S3
    │   ├── variables.tf
    │   └── outputs.tf
    └── regional/             # Regional resources (deploy per region)
        ├── main.tf           # ECS, SQS, EventBridge (uses modules/)
        ├── variables.tf
        └── outputs.tf
```

---

## 🎯 Why Both Folders?

### `modules/` - Reusable Building Blocks

**Purpose**: Reusable Terraform modules that define common infrastructure patterns.

**Examples**:
- `modules/ecs-service/` - Creates an ECS Fargate service (used by both single-region and multi-region)
- `modules/dynamodb/` - Creates a DynamoDB table (used by single-region)
- `modules/s3/` - Creates an S3 bucket (used by single-region)

**Characteristics**:
- ✅ Reusable across different deployments
- ✅ Encapsulate common patterns
- ✅ Can be used by both single-region and multi-region deployments
- ✅ DRY (Don't Repeat Yourself) principle

**Usage**:
```hcl
# In main.tf or multi-region/regional/main.tf
module "ecs_service" {
  source = "./modules/ecs-service"  # Uses the reusable module
  
  name = "agent-host"
  # ... other parameters
}
```

### `multi-region/` - Deployment Configurations

**Purpose**: Actual deployment configurations that USE the modules to create infrastructure.

**Structure**:
- `global/` - Deploys global resources (DynamoDB Global Tables, Central S3)
- `regional/` - Deploys regional resources (ECS, SQS, etc.) using modules

**Characteristics**:
- ✅ Deployment-specific configurations
- ✅ Uses modules from `modules/` folder
- ✅ Can be deployed multiple times (once per region)
- ✅ Contains environment-specific variables

**Usage**:
```hcl
# In multi-region/regional/main.tf
module "vpc" {
  source = "../../modules/vpc"  # References modules folder
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}
```

---

## 🔄 Relationship Between Folders

```
┌─────────────────────────────────────────────────────────┐
│                    modules/                              │
│         (Reusable Building Blocks)                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ ECS      │  │ DynamoDB │  │ S3       │              │
│  │ Service  │  │ Module   │  │ Module   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
         │                    │                    │
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              │ USES
                              │
         ┌────────────────────┴────────────────────┐
         │                                          │
┌────────┴──────────┐              ┌────────────────┴──────────┐
│  main.tf          │              │  multi-region/            │
│  (Single Region)  │              │  (Multi-Region)           │
│                   │              │                           │
│  Uses modules/    │              │  Uses modules/            │
│  for single       │              │  for multiple regions     │
│  region deploy    │              │                           │
└───────────────────┘              └───────────────────────────┘
```

---

## 📊 Comparison

| Aspect | `modules/` | `multi-region/` |
|--------|------------|-----------------|
| **Purpose** | Reusable components | Deployment configurations |
| **Reusability** | High (used by multiple deployments) | Low (specific to multi-region) |
| **Deployment** | Not deployed directly | Deployed directly |
| **Examples** | ECS service, DynamoDB table | Global tables, Regional ECS clusters |
| **Variables** | Generic parameters | Environment/region-specific |

---

## 🎯 When to Use What

### Use `modules/` when:
- ✅ Creating reusable infrastructure patterns
- ✅ Want to avoid code duplication
- ✅ Need the same component in multiple places
- ✅ Building a library of common patterns

### Use `multi-region/` when:
- ✅ Deploying to multiple regions
- ✅ Need global resources (DynamoDB Global Tables, Central S3)
- ✅ Want separate deployments per region
- ✅ Need region-specific configurations

### Use root `main.tf` when:
- ✅ Single-region deployment (simpler setup)
- ✅ Development/testing
- ✅ Don't need multi-region capabilities

---

## 🔧 Example: How They Work Together

### Step 1: Define Module (`modules/ecs-service/main.tf`)
```hcl
# Reusable module
variable "name" {}
variable "environment" {}
# ... other variables

resource "aws_ecs_service" "main" {
  name = var.name
  # ... configuration
}
```

### Step 2: Use Module (`multi-region/regional/main.tf`)
```hcl
# Deployment configuration
module "agent_host" {
  source = "../../modules/ecs-service"  # Uses the module
  
  name        = "agent-host"
  environment = var.environment
  # ... other parameters
}
```

---

## 💡 Why This Structure?

### Benefits:

1. **DRY Principle**: Write modules once, use everywhere
2. **Consistency**: Same patterns across deployments
3. **Maintainability**: Update module once, affects all deployments
4. **Flexibility**: Can have both single-region and multi-region deployments
5. **Separation of Concerns**: Modules = what, Deployments = where/how

### Trade-offs:

- ⚠️ Slightly more complex structure
- ⚠️ Need to understand module vs deployment distinction
- ✅ But much more maintainable and scalable

---

## 🚀 Deployment Paths

### Option 1: Single-Region (Simple)
```bash
cd infra/terraform
terraform apply  # Uses main.tf + modules/
```

### Option 2: Multi-Region (Production)
```bash
# Step 1: Deploy global resources
cd infra/terraform/multi-region/global
terraform apply

# Step 2: Deploy regional resources (per region)
cd infra/terraform/multi-region/regional
terraform workspace new us-east-1
terraform apply -var="aws_region=us-east-1" ...
```

---

## 📝 Summary

- **`modules/`** = Reusable building blocks (like LEGO pieces)
- **`multi-region/`** = Deployment configurations that use those blocks
- **Root `main.tf`** = Single-region deployment (also uses modules)

**Think of it like**:
- `modules/` = Library of functions
- `multi-region/` = Programs that call those functions
- Both are needed because modules provide reusability, deployments provide actual infrastructure

---

**Last Updated**: Current Session
