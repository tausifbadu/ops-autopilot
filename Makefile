# Ops AutoPilot - Makefile
# Common operations for development, testing, and deployment

.PHONY: help install setup test format lint clean docker-build docker-up docker-down docker-logs docker-restart local-run terraform-init terraform-plan terraform-apply terraform-destroy terraform-workspace

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
TERRAFORM := terraform
ENVIRONMENT ?= dev
AWS_REGION ?= us-east-1
TERRAFORM_DIR := infra/terraform
MULTI_REGION_GLOBAL := infra/terraform/multi-region/global
MULTI_REGION_REGIONAL := infra/terraform/multi-region/regional

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(BLUE)Ops AutoPilot - Available Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(BLUE)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

install: ## Install Python dependencies for all components
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@echo "$(YELLOW)Installing shared package...$(NC)"
	cd shared && $(PIP) install -e .
	@echo "$(YELLOW)Installing agent-host...$(NC)"
	cd agent-host && $(PIP) install -e .
	@echo "$(YELLOW)Installing MCP servers...$(NC)"
	cd mcp-servers/orchestration-sfn && $(PIP) install -e . || true
	cd mcp-servers/observability-cloudwatch && $(PIP) install -e . || true
	cd mcp-servers/data-execution-glue-emr && $(PIP) install -e . || true
	cd mcp-servers/devtools-github && $(PIP) install -e . || true
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

setup: install ## Complete setup (install dependencies, create directories)
	@echo "$(BLUE)Setting up project...$(NC)"
	@mkdir -p ./evidence
	@mkdir -p ./logs
	@echo "$(GREEN)✓ Project setup complete$(NC)"

##@ Docker Operations

docker-build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up: ## Start all MCP servers with Docker Compose
	@echo "$(BLUE)Starting MCP servers...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ MCP servers started$(NC)"
	@echo "$(YELLOW)Waiting for services to be healthy...$(NC)"
	@sleep 5
	@make docker-health

docker-down: ## Stop all Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Docker containers stopped$(NC)"

docker-restart: docker-down docker-up ## Restart all Docker containers

docker-logs: ## Show logs from all Docker containers
	$(DOCKER_COMPOSE) logs -f

docker-logs-mcp: ## Show logs from MCP servers only
	$(DOCKER_COMPOSE) logs -f orchestration-sfn observability-cloudwatch data-execution-glue-emr devtools-github

docker-health: ## Check health of all MCP servers
	@echo "$(BLUE)Checking MCP server health...$(NC)"
	@curl -s http://localhost:8001/health > /dev/null && echo "$(GREEN)✓ orchestration-sfn (8001) - Healthy$(NC)" || echo "$(RED)✗ orchestration-sfn (8001) - Unhealthy$(NC)"
	@curl -s http://localhost:8002/health > /dev/null && echo "$(GREEN)✓ observability-cloudwatch (8002) - Healthy$(NC)" || echo "$(RED)✗ observability-cloudwatch (8002) - Unhealthy$(NC)"
	@curl -s http://localhost:8003/health > /dev/null && echo "$(GREEN)✓ data-execution-glue-emr (8003) - Healthy$(NC)" || echo "$(RED)✗ data-execution-glue-emr (8003) - Unhealthy$(NC)"
	@curl -s http://localhost:8007/health > /dev/null && echo "$(GREEN)✓ devtools-github (8007) - Healthy$(NC)" || echo "$(RED)✗ devtools-github (8007) - Unhealthy$(NC)"

docker-clean: ## Remove all Docker containers, volumes, and images
	@echo "$(YELLOW)Removing Docker containers and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi all
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

##@ Local Development

local-run: ## Run Agent Host locally with sample event
	@echo "$(BLUE)Running Agent Host locally...$(NC)"
	@if [ -z "$(EVENT_FILE)" ]; then \
		echo "$(YELLOW)Using default event file...$(NC)"; \
		cd agent-host && $(PYTHON) -m agent_host.main --local-file src/agent_host/sample_events/pipeline_failure.json; \
	else \
		echo "$(YELLOW)Using event file: $(EVENT_FILE)$(NC)"; \
		cd agent-host && $(PYTHON) -m agent_host.main --local-file $(EVENT_FILE); \
	fi

local-run-sqs: ## Run Agent Host in SQS polling mode (AWS mode)
	@echo "$(BLUE)Running Agent Host in SQS mode...$(NC)"
	cd agent-host && $(PYTHON) -m agent_host.main --sqs

local-dev: docker-up local-run ## Start MCP servers and run Agent Host locally

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	cd agent-host && $(PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	cd agent-host && $(PYTHON) -m pytest tests/ -v -k "not integration"
	@echo "$(GREEN)✓ Unit tests complete$(NC)"

test-integration: ## Run integration tests (requires MCP servers)
	@echo "$(BLUE)Running integration tests...$(NC)"
	@echo "$(YELLOW)Note: MCP servers must be running$(NC)"
	cd agent-host && $(PYTHON) -m pytest tests/ -v -k "integration"
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	cd agent-host && $(PYTHON) -m pytest tests/ --cov=agent_host --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

##@ Code Quality

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	@if command -v black > /dev/null; then \
		black agent-host/src agent-host/tests mcp-servers/*/src shared/src; \
		echo "$(GREEN)✓ Code formatted$(NC)"; \
	else \
		echo "$(RED)✗ black not installed. Run: pip install black$(NC)"; \
	fi

lint: ## Lint code with ruff/flake8
	@echo "$(BLUE)Linting code...$(NC)"
	@if command -v ruff > /dev/null; then \
		ruff check agent-host/src agent-host/tests mcp-servers/*/src shared/src; \
		echo "$(GREEN)✓ Linting complete$(NC)"; \
	elif command -v flake8 > /dev/null; then \
		flake8 agent-host/src agent-host/tests mcp-servers/*/src shared/src; \
		echo "$(GREEN)✓ Linting complete$(NC)"; \
	else \
		echo "$(RED)✗ ruff/flake8 not installed. Run: pip install ruff$(NC)"; \
	fi

type-check: ## Type check with mypy
	@echo "$(BLUE)Type checking...$(NC)"
	@if command -v mypy > /dev/null; then \
		mypy agent-host/src shared/src; \
		echo "$(GREEN)✓ Type checking complete$(NC)"; \
	else \
		echo "$(RED)✗ mypy not installed. Run: pip install mypy$(NC)"; \
	fi

check: format lint type-check ## Run all code quality checks

##@ Terraform Operations

terraform-init: ## Initialize Terraform
	@echo "$(BLUE)Initializing Terraform...$(NC)"
	cd $(TERRAFORM_DIR) && $(TERRAFORM) init
	@echo "$(GREEN)✓ Terraform initialized$(NC)"

terraform-plan: ## Plan Terraform changes
	@echo "$(BLUE)Planning Terraform changes...$(NC)"
	cd $(TERRAFORM_DIR) && $(TERRAFORM) plan \
		-var="environment=$(ENVIRONMENT)" \
		-var="aws_region=$(AWS_REGION)"

terraform-apply: ## Apply Terraform changes
	@echo "$(BLUE)Applying Terraform changes...$(NC)"
	cd $(TERRAFORM_DIR) && $(TERRAFORM) apply \
		-var="environment=$(ENVIRONMENT)" \
		-var="aws_region=$(AWS_REGION)" \
		-auto-approve
	@echo "$(GREEN)✓ Terraform applied$(NC)"

terraform-destroy: ## Destroy Terraform infrastructure
	@echo "$(RED)WARNING: This will destroy all infrastructure!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd $(TERRAFORM_DIR) && $(TERRAFORM) destroy \
			-var="environment=$(ENVIRONMENT)" \
			-var="aws_region=$(AWS_REGION)"; \
	fi

terraform-validate: ## Validate Terraform configuration
	@echo "$(BLUE)Validating Terraform...$(NC)"
	cd $(TERRAFORM_DIR) && $(TERRAFORM) validate
	@echo "$(GREEN)✓ Terraform configuration valid$(NC)"

terraform-fmt: ## Format Terraform files
	@echo "$(BLUE)Formatting Terraform files...$(NC)"
	cd $(TERRAFORM_DIR) && $(TERRAFORM) fmt -recursive
	@echo "$(GREEN)✓ Terraform files formatted$(NC)"

##@ Multi-Region Terraform

tf-global-init: ## Initialize global Terraform resources
	@echo "$(BLUE)Initializing global Terraform...$(NC)"
	cd $(MULTI_REGION_GLOBAL) && $(TERRAFORM) init
	@echo "$(GREEN)✓ Global Terraform initialized$(NC)"

tf-global-plan: ## Plan global Terraform changes
	@echo "$(BLUE)Planning global Terraform changes...$(NC)"
	cd $(MULTI_REGION_GLOBAL) && $(TERRAFORM) plan \
		-var="environment=$(ENVIRONMENT)" \
		-var="primary_region=$(AWS_REGION)"

tf-global-apply: ## Apply global Terraform changes
	@echo "$(BLUE)Applying global Terraform changes...$(NC)"
	cd $(MULTI_REGION_GLOBAL) && $(TERRAFORM) apply \
		-var="environment=$(ENVIRONMENT)" \
		-var="primary_region=$(AWS_REGION)" \
		-auto-approve
	@echo "$(GREEN)✓ Global Terraform applied$(NC)"

tf-regional-init: ## Initialize regional Terraform resources
	@echo "$(BLUE)Initializing regional Terraform...$(NC)"
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) init
	@echo "$(GREEN)✓ Regional Terraform initialized$(NC)"

tf-regional-plan: ## Plan regional Terraform changes
	@echo "$(BLUE)Planning regional Terraform changes for $(AWS_REGION)...$(NC)"
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) plan \
		-var="aws_region=$(AWS_REGION)" \
		-var="environment=$(ENVIRONMENT)" \
		-var="global_dynamodb_tables.workflow_registry=$(DYNAMODB_REGISTRY)" \
		-var="global_dynamodb_tables.incidents=$(DYNAMODB_INCIDENTS)" \
		-var="global_dynamodb_tables.baselines=$(DYNAMODB_BASELINES)" \
		-var="global_s3_evidence_bucket=$(S3_EVIDENCE_BUCKET)" \
		-var="dynamodb_primary_region=$(DYNAMODB_PRIMARY_REGION)" \
		-var="s3_evidence_region=$(S3_EVIDENCE_REGION)"

tf-regional-apply: ## Apply regional Terraform changes
	@echo "$(BLUE)Applying regional Terraform changes for $(AWS_REGION)...$(NC)"
	@if [ -z "$(DYNAMODB_REGISTRY)" ] || [ -z "$(S3_EVIDENCE_BUCKET)" ]; then \
		echo "$(RED)✗ Error: Global resources must be deployed first$(NC)"; \
		echo "$(YELLOW)Required variables: DYNAMODB_REGISTRY, DYNAMODB_INCIDENTS, DYNAMODB_BASELINES, S3_EVIDENCE_BUCKET, DYNAMODB_PRIMARY_REGION, S3_EVIDENCE_REGION$(NC)"; \
		exit 1; \
	fi
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) apply \
		-var="aws_region=$(AWS_REGION)" \
		-var="environment=$(ENVIRONMENT)" \
		-var="global_dynamodb_tables.workflow_registry=$(DYNAMODB_REGISTRY)" \
		-var="global_dynamodb_tables.incidents=$(DYNAMODB_INCIDENTS)" \
		-var="global_dynamodb_tables.baselines=$(DYNAMODB_BASELINES)" \
		-var="global_s3_evidence_bucket=$(S3_EVIDENCE_BUCKET)" \
		-var="dynamodb_primary_region=$(DYNAMODB_PRIMARY_REGION)" \
		-var="s3_evidence_region=$(S3_EVIDENCE_REGION)" \
		-auto-approve
	@echo "$(GREEN)✓ Regional Terraform applied$(NC)"

tf-workspace-list: ## List Terraform workspaces
	@echo "$(BLUE)Terraform workspaces:$(NC)"
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) workspace list

tf-workspace-new: ## Create new Terraform workspace (use WORKSPACE=region-name)
	@if [ -z "$(WORKSPACE)" ]; then \
		echo "$(RED)✗ Error: WORKSPACE variable required$(NC)"; \
		echo "$(YELLOW)Usage: make tf-workspace-new WORKSPACE=us-west-2$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating workspace: $(WORKSPACE)$(NC)"
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) workspace new $(WORKSPACE)
	@echo "$(GREEN)✓ Workspace created$(NC)"

tf-workspace-select: ## Select Terraform workspace (use WORKSPACE=region-name)
	@if [ -z "$(WORKSPACE)" ]; then \
		echo "$(RED)✗ Error: WORKSPACE variable required$(NC)"; \
		echo "$(YELLOW)Usage: make tf-workspace-select WORKSPACE=us-west-2$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Selecting workspace: $(WORKSPACE)$(NC)"
	cd $(MULTI_REGION_REGIONAL) && $(TERRAFORM) workspace select $(WORKSPACE)
	@echo "$(GREEN)✓ Workspace selected$(NC)"

##@ Cleanup

clean: ## Clean temporary files and caches
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-evidence: ## Clean evidence directory (local mode)
	@echo "$(YELLOW)Cleaning evidence directory...$(NC)"
	rm -rf ./evidence/*
	@echo "$(GREEN)✓ Evidence directory cleaned$(NC)"

clean-all: clean clean-evidence docker-clean ## Clean everything (files, evidence, Docker)

##@ Documentation

docs-serve: ## Serve documentation locally (requires mkdocs)
	@if command -v mkdocs > /dev/null; then \
		mkdocs serve; \
	else \
		echo "$(RED)✗ mkdocs not installed. Run: pip install mkdocs$(NC)"; \
	fi

docs-build: ## Build documentation
	@if command -v mkdocs > /dev/null; then \
		mkdocs build; \
	else \
		echo "$(RED)✗ mkdocs not installed. Run: pip install mkdocs$(NC)"; \
	fi

##@ Quick Commands

quick-start: docker-up ## Quick start: Start MCP servers and check health
	@echo "$(GREEN)✓ Quick start complete!$(NC)"
	@echo "$(YELLOW)Run 'make local-run' to process a sample event$(NC)"

quick-test: docker-up test ## Quick test: Start servers and run tests

quick-dev: setup docker-up local-run ## Quick dev: Full setup and run

##@ Information

info: ## Show project information
	@echo "$(BLUE)Ops AutoPilot - Project Information$(NC)"
	@echo ""
	@echo "$(GREEN)Components:$(NC)"
	@echo "  • Agent Host: $(BLUE)agent-host/$(NC)"
	@echo "  • MCP Servers: $(BLUE)mcp-servers/$(NC)"
	@echo "  • Shared: $(BLUE)shared/$(NC)"
	@echo "  • Infrastructure: $(BLUE)infra/terraform/$(NC)"
	@echo ""
	@echo "$(GREEN)MCP Servers:$(NC)"
	@echo "  • orchestration-sfn: $(BLUE)http://localhost:8001$(NC)"
	@echo "  • observability-cloudwatch: $(BLUE)http://localhost:8002$(NC)"
	@echo "  • data-execution-glue-emr: $(BLUE)http://localhost:8003$(NC)"
	@echo "  • devtools-github: $(BLUE)http://localhost:8007$(NC)"
	@echo ""
	@echo "$(GREEN)Useful Commands:$(NC)"
	@echo "  • $(BLUE)make help$(NC) - Show all commands"
	@echo "  • $(BLUE)make quick-start$(NC) - Start MCP servers"
	@echo "  • $(BLUE)make local-run$(NC) - Run Agent Host locally"
	@echo "  • $(BLUE)make test$(NC) - Run tests"

version: ## Show version information
	@echo "$(BLUE)Ops AutoPilot$(NC)"
	@echo "  Python: $$($(PYTHON) --version 2>&1)"
	@echo "  Docker: $$($(DOCKER_COMPOSE) --version 2>&1)"
	@echo "  Terraform: $$($(TERRAFORM) version -json 2>/dev/null | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4 || echo 'not installed')"
