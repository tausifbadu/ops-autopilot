#!/usr/bin/env bash
# Build and push all ECS images to ECR. Run from repo root.
# Requires: Docker, AWS CLI, and AWS credentials with ECR push access.
# Usage: ./scripts/push-ecr.sh [region]

set -e
REGION="${1:-${AWS_REGION:-us-east-1}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_HOST="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "Logging into ECR ($ECR_HOST)..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_HOST"

cd "$REPO_ROOT"

build_push() {
  local path="$1"
  local repo="$2"
  local img="${ECR_HOST}/${repo}:latest"
  echo "Building $path..."
  docker build -t "$img" "$path"
  echo "Pushing $img..."
  docker push "$img"
}

build_push "agent-host" "ops-autopilot/agent-host"
build_push "mcp-servers/orchestration-sfn" "ops-autopilot/mcp-orchestration-sfn"
build_push "mcp-servers/data-execution-glue-emr" "ops-autopilot/mcp-data-execution-glue-emr"
build_push "mcp-servers/observability-cloudwatch" "ops-autopilot/mcp-observability-cloudwatch"
build_push "mcp-servers/devtools-github" "ops-autopilot/mcp-devtools-github"

echo "All images pushed to ECR."
