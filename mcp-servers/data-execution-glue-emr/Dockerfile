# Dockerfile for data-execution-glue-emr MCP server

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        boto3 \
        pydantic \
        httpx

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8003

# Set working directory to source
WORKDIR /app/src

# Run the application
# Note: For ECS Fargate, port is configurable via PORT environment variable
CMD ["sh", "-c", "uvicorn data_execution.app:app --host 0.0.0.0 --port ${PORT:-8003}"]
