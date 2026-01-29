# Dockerfile for Agent Host. Build from repo root: docker build -f agent-host/Dockerfile -t <image> .

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package then agent-host (needs shared)
COPY shared/ ./shared/
COPY agent-host/ ./agent-host/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./shared && \
    pip install --no-cache-dir ./agent-host

# Ensure Python finds shared package (fallback if site-packages path differs in runtime)
ENV PYTHONPATH=/app/shared/src

WORKDIR /app/agent-host/src

# ECS runs this; port/env come from task definition
CMD ["python", "-m", "agent_host.main", "--sqs"]
