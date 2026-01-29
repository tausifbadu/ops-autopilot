# Build and push all ECS images to ECR. Run from repo root.
# Requires: Docker, AWS CLI, and AWS credentials with ECR push access.
# Usage: .\scripts\push-ecr.ps1 [-Region us-east-1]

param(
    [string]$Region = (Get-ChildItem Env:AWS_REGION -ErrorAction SilentlyContinue).Value
)
if (-not $Region) { $Region = "us-east-1" }

$AccountId = (aws sts get-caller-identity --query Account --output text 2>$null)
if (-not $AccountId) {
    Write-Error "Could not get AWS account ID. Run 'aws configure' or set AWS credentials."
    exit 1
}

$EcrHost = "${AccountId}.dkr.ecr.${Region}.amazonaws.com"

Write-Host "Logging into ECR ($EcrHost)..."
# Use cmd for the pipe so the token is not corrupted (PowerShell pipe can cause 400)
cmd /c "aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrHost"
if ($LASTEXITCODE -ne 0) { exit 1 }

# Agent-host must be built from repo root (needs shared/). Others build from their dir.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $RepoRoot
try {
    $img = "${EcrHost}/ops-autopilot/agent-host:latest"
    Write-Host "Building agent-host (from repo root, no cache)..."
    docker build --no-cache -f agent-host/Dockerfile -t $img .
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed: agent-host"; exit 1 }
    Write-Host "Pushing $img..."
    docker push $img
    if ($LASTEXITCODE -ne 0) { Write-Error "Push failed: agent-host"; exit 1 }
} finally {
    Pop-Location
}

$Services = @(
    @{ Name = "mcp-orchestration-sfn"; Path = "mcp-servers/orchestration-sfn"; Repo = "ops-autopilot/mcp-orchestration-sfn" },
    @{ Name = "mcp-data-execution-glue-emr"; Path = "mcp-servers/data-execution-glue-emr"; Repo = "ops-autopilot/mcp-data-execution-glue-emr" },
    @{ Name = "mcp-observability-cloudwatch"; Path = "mcp-servers/observability-cloudwatch"; Repo = "ops-autopilot/mcp-observability-cloudwatch" },
    @{ Name = "mcp-devtools-github"; Path = "mcp-servers/devtools-github"; Repo = "ops-autopilot/mcp-devtools-github" }
)

Push-Location $RepoRoot
try {
    foreach ($svc in $Services) {
        $repo = $svc["Repo"]
        $img = $EcrHost + "/" + $repo + ":latest"
        Write-Host "Building $($svc.Name)..."
        docker build -t $img $svc.Path
        if ($LASTEXITCODE -ne 0) { Write-Error "Build failed: $($svc.Name)"; exit 1 }
        Write-Host "Pushing $img..."
        docker push $img
        if ($LASTEXITCODE -ne 0) { Write-Error "Push failed: $($svc.Name)"; exit 1 }
    }
    Write-Host "All images pushed to ECR."
} finally {
    Pop-Location
}
