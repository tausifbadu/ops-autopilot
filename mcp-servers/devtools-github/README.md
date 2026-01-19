# GitHub MCP Server

MCP (Model Context Protocol) server for GitHub operations. Provides safe, typed, auditable tool APIs for code search, file reading, commit analysis, and PR creation.

## Overview

The GitHub MCP Server enables the Agent Host to:
- Search code in repositories
- Read file contents
- Analyze recent commits and changes
- Get file blame information
- Create branches and pull requests (for auto-fix workflows)

## Features

- ✅ **Code Search**: Search code by query, repository, and file extension
- ✅ **File Reading**: Read file contents with automatic base64 decoding
- ✅ **Commit Analysis**: Get recent commits with time and file filters
- ✅ **Git Blame**: Analyze recent changes to files
- ✅ **Branch Management**: Create branches for fixes
- ✅ **PR Creation**: Create pull requests with descriptions
- ✅ **Repository Allowlist**: Security boundary to restrict access
- ✅ **Type-safe APIs**: Pydantic schemas for request/response validation
- ✅ **Structured Logging**: Consistent, auditable logging
- ✅ **Health Checks**: `/health` endpoint for monitoring

## Architecture

```
Agent Host
    ↓
MCP Client (HTTP)
    ↓
GitHub MCP Server (FastAPI)
    ↓
GitHub API (REST)
```

## Tools

### 1. `search_code`

Search code in a repository using GitHub's code search API.

**Request:**
```json
{
  "tool": "search_code",
  "arguments": {
    "query": "ValueError",
    "repository": "owner/repo",
    "file_extension": "py"
  }
}
```

**Response:**
```json
{
  "result": {
    "items": [
      {
        "name": "main.py",
        "path": "src/main.py",
        "sha": "abc123...",
        "url": "https://api.github.com/repos/owner/repo/contents/src/main.py",
        "git_url": "https://api.github.com/repos/owner/repo/git/blobs/abc123",
        "html_url": "https://github.com/owner/repo/blob/main/src/main.py",
        "repository": {
          "full_name": "owner/repo"
        }
      }
    ]
  }
}
```

### 2. `read_file`

Read file contents from a repository.

**Request:**
```json
{
  "tool": "read_file",
  "arguments": {
    "repository": "owner/repo",
    "file_path": "src/main.py",
    "ref": "main"
  }
}
```

**Response:**
```json
{
  "result": {
    "name": "main.py",
    "path": "src/main.py",
    "sha": "abc123...",
    "size": 1234,
    "url": "https://api.github.com/repos/owner/repo/contents/src/main.py",
    "html_url": "https://github.com/owner/repo/blob/main/src/main.py",
    "git_url": "https://api.github.com/repos/owner/repo/git/blobs/abc123",
    "download_url": "https://raw.githubusercontent.com/owner/repo/main/src/main.py",
    "type": "file",
    "content": "def main():\n    print('Hello')\n",
    "encoding": "base64"
  }
}
```

**Note:** Content is automatically decoded from base64 if present.

### 3. `get_recent_commits`

Get recent commits for a repository or specific file.

**Request:**
```json
{
  "tool": "get_recent_commits",
  "arguments": {
    "repository": "owner/repo",
    "file_path": "src/main.py",
    "since": "2024-01-01T00:00:00Z",
    "limit": 20
  }
}
```

**Response:**
```json
{
  "result": {
    "commits": [
      {
        "sha": "abc123def456...",
        "commit": {
          "message": "Fix: Handle ValueError in data processing",
          "author": {
            "name": "John Doe",
            "email": "john@example.com",
            "date": "2024-01-15T10:00:00Z"
          }
        },
        "author": {
          "login": "johndoe"
        },
        "html_url": "https://github.com/owner/repo/commit/abc123"
      }
    ]
  }
}
```

### 4. `get_file_blame`

Get git blame information and recent changes for a file.

**Request:**
```json
{
  "tool": "get_file_blame",
  "arguments": {
    "repository": "owner/repo",
    "file_path": "src/main.py",
    "ref": "main"
  }
}
```

**Response:**
```json
{
  "result": {
    "file_path": "src/main.py",
    "recent_changes": [
      {
        "sha": "abc123",
        "message": "Fix: Handle ValueError",
        "author": "John Doe",
        "date": "2024-01-15T10:00:00Z"
      }
    ],
    "total_commits": 15
  }
}
```

### 5. `create_branch`

Create a new branch from a base reference.

**Request:**
```json
{
  "tool": "create_branch",
  "arguments": {
    "repository": "owner/repo",
    "branch_name": "fix/bug-123",
    "from_ref": "main"
  }
}
```

**Response:**
```json
{
  "result": {
    "ref": "refs/heads/fix/bug-123",
    "node_id": "REF_kwDO...",
    "url": "https://api.github.com/repos/owner/repo/git/refs/heads/fix/bug-123",
    "object": {
      "sha": "abc123...",
      "type": "commit",
      "url": "https://api.github.com/repos/owner/repo/git/commits/abc123"
    }
  }
}
```

### 6. `create_pr`

Create a pull request.

**Request:**
```json
{
  "tool": "create_pr",
  "arguments": {
    "repository": "owner/repo",
    "title": "Fix: Handle ValueError in data processing",
    "description": "Fixes issue where ValueError was not caught...",
    "head_branch": "fix/bug-123",
    "base_branch": "main"
  }
}
```

**Response:**
```json
{
  "result": {
    "pr_number": 42,
    "pr_url": "https://github.com/owner/repo/pull/42",
    "state": "open"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8007` | No |
| `GITHUB_TOKEN` | GitHub personal access token | `None` | **Yes** |
| `GITHUB_API_URL` | GitHub API base URL (for GitHub Enterprise) | `https://api.github.com` | No |
| `ALLOWLIST_ENABLED` | Enable repository allowlist | `true` | No |
| `ALLOWLIST_FILE` | Path to allowlist file | `None` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### GitHub Token Setup

1. **Create a Personal Access Token:**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with scopes:
     - `repo` (full control of private repositories)
     - `read:org` (if accessing organization repos)

2. **Set Environment Variable:**
   ```bash
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
   ```

3. **For GitHub Enterprise:**
   ```bash
   export GITHUB_API_URL=https://github.example.com/api/v3
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
   ```

## Security

### Repository Allowlist

The server supports an allowlist to restrict access to specific repositories:

```python
# In allowlist.py
allowlist.add_repository("owner/repo")
allowlist.add_repository("owner/another-repo")
```

**MVP Behavior:**
- If allowlist is empty → allows all (for development)
- If allowlist has entries → only allows listed repositories
- Can be disabled with `ALLOWLIST_ENABLED=false`

### Token Security

- **Never commit tokens to version control**
- Use environment variables or secrets management
- Rotate tokens regularly
- Use least-privilege scopes

## Local Development

### Using Docker Compose

```bash
# Set GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Start the server
docker-compose up devtools-github

# Or in detached mode
docker-compose up -d devtools-github
```

### Manual Docker Build

```bash
cd mcp-servers/devtools-github
docker build -t mcp-devtools-github .
docker run -p 8007:8007 \
  -e GITHUB_TOKEN=ghp_xxxxxxxxxxxxx \
  mcp-devtools-github
```

### Direct Python Execution

```bash
cd mcp-servers/devtools-github
pip install -e .
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
uvicorn devtools_github.app:app --host 0.0.0.0 --port 8007
```

## Testing

### Health Check

```bash
curl http://localhost:8007/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "devtools-github"
}
```

### Test Code Search

```bash
curl -X POST http://localhost:8007/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_code",
    "arguments": {
      "query": "ValueError",
      "repository": "owner/repo"
    }
  }'
```

### Test File Reading

```bash
curl -X POST http://localhost:8007/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "read_file",
    "arguments": {
      "repository": "owner/repo",
      "file_path": "README.md"
    }
  }'
```

## AWS Deployment

### ECS Fargate

The server is designed to run on ECS Fargate:

1. **Build and push Docker image:**
   ```bash
   docker build -t devtools-github .
   docker tag devtools-github:latest <ECR_URI>/devtools-github:latest
   docker push <ECR_URI>/devtools-github:latest
   ```

2. **Terraform Configuration:**
   See `infra/terraform/main.tf` for ECS service definition.

3. **Environment Variables:**
   - Set `GITHUB_TOKEN` via AWS Secrets Manager or ECS task definition
   - Store token securely (never in plain text)

### Service Discovery

In AWS, the server is accessible via:
- Service name: `mcp-devtools-github`
- Port: `8007`
- Health check: `http://mcp-devtools-github:8007/health`

## Use Cases

### 1. Code Bug Investigation

When Pipeline RCA Agent detects `CODE_REGRESSION`:

```python
# Search for error-related code
search_results = github_client.search_code(
    query="ValueError",
    repository="owner/repo"
)

# Read relevant files
file_content = github_client.read_file(
    repository="owner/repo",
    file_path="src/main.py"
)

# Analyze recent changes
commits = github_client.get_recent_commits(
    repository="owner/repo",
    file_path="src/main.py",
    since="2024-01-01T00:00:00Z"
)
```

### 2. Auto-Fix Workflow

```python
# Create branch for fix
branch = github_client.create_branch(
    repository="owner/repo",
    branch_name="fix/bug-123",
    from_ref="main"
)

# (Commit changes via git or GitHub API)

# Create PR
pr = github_client.create_pr(
    repository="owner/repo",
    title="Fix: Handle ValueError",
    description="Fixes issue where ValueError was not caught...",
    head_branch="fix/bug-123",
    base_branch="main"
)
```

## Error Handling

The server returns structured error responses:

```json
{
  "detail": "Repository not in allowlist: owner/repo"
}
```

Common error codes:
- `400`: Bad request (validation error)
- `403`: Forbidden (not in allowlist or insufficient permissions)
- `404`: Not found (repository or file doesn't exist)
- `500`: Internal server error

## Rate Limiting

GitHub API has rate limits:
- **Authenticated requests**: 5,000 requests/hour
- **Unauthenticated requests**: 60 requests/hour

The server logs warnings when approaching rate limits. Consider implementing:
- Request caching
- Exponential backoff
- Rate limit monitoring

## Logging

Structured logging format:
```
2024-01-15 10:00:00 - devtools_github.app - INFO - Tool call: search_code with arguments: {...}
2024-01-15 10:00:01 - devtools_github.github_client - INFO - Found 5 code search results for 'ValueError' in owner/repo
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: `http://localhost:8007/docs`
- ReDoc: `http://localhost:8007/redoc`

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `httpx`: HTTP client for GitHub API
- `pydantic`: Data validation

## GitHub API Reference

This server uses GitHub REST API v3:
- [Code Search API](https://docs.github.com/en/rest/search/search#search-code)
- [Contents API](https://docs.github.com/en/rest/repos/contents)
- [Commits API](https://docs.github.com/en/rest/commits/commits)
- [Git References API](https://docs.github.com/en/rest/git/refs)
- [Pull Requests API](https://docs.github.com/en/rest/pulls/pulls)

## License

Part of the ops-autopilot project.
