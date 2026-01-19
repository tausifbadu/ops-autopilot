# Dockerfile for Agent Host (optional, for containerized deployment)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir httpx pydantic boto3

# Copy application code
COPY src/ ./src/

# Set working directory
WORKDIR /app/src

# For ECS Fargate production deployment
# CMD will be set in ECS task definition or via environment variable
# CMD ["python", "-m", "agent_host.main"]
