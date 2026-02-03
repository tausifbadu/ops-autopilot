# Agent Host

Runs the Ops AutoPilot agent: processes events from SQS (AWS) or from a local JSON file.

## Running with SQS (AWS)

Set the incidents queue URL and AWS identity, then run:

```bash
export SQS_QUEUE_INCIDENTS="https://sqs.<region>.amazonaws.com/<account>/incidents.fifo"
python -m agent_host.main --sqs
```

On Windows (PowerShell):

```powershell
$env:SQS_QUEUE_INCIDENTS = "https://sqs.<region>.amazonaws.com/<account>/incidents.fifo"
python -m agent_host.main --sqs
```

### AWS credentials

Use either **credentials file**, **env keys**, or a **profile**:

- **aws configure (recommended):** Run `aws configure` (or `aws sso login`) so `~/.aws/credentials` (or SSO cache) is set. The agent-host uses the same credential chain as the CLI. Do **not** put `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` in `.env` if they are stale—env vars override the file and can cause ExpiredToken.
- **Keys in shell:** Export `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_SESSION_TOKEN` in the shell (not in `.env`) so they take precedence and stay fresh.
- **Profile:** Set `AWS_PROFILE` and run `aws sso login` if you use a named profile.

Then run: `python -m agent_host.main --sqs`

### MCP server credentials (Glue/EMR evidence)

When processing Glue job failures, the agent-host calls the **data-execution-glue-emr** MCP server. If you see `Tool call failed: Unable to locate credentials`, the MCP server has no valid AWS credentials.

- **Docker:** Pass keys into the container via env: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_SESSION_TOKEN`. Set them in `.env` or in the shell before `docker-compose up`. Alternatively mount `~/.aws` and use `AWS_PROFILE` (after `aws sso login` on the host).
- **Run locally:** Set the same env vars (keys or `AWS_PROFILE`) in the shell where you start the data-execution server. See `mcp-servers/data-execution-glue-emr/README.md` for details.

## Running with a local event file

```bash
python -m agent_host.main --local-file path/to/event.json
```
