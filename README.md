# selectel-mcp

An [MCP](https://modelcontextprotocol.io) server that gives an AI agent (Claude Code,
Claude Desktop, etc.) controlled access to a [Selectel](https://selectel.ru) cloud
account: OpenStack cloud servers, S3 object storage, and account billing.

## What it can do

| Area | Tools |
|------|-------|
| **Compute** (OpenStack) | `list_servers`, `get_server`, `list_flavors`, `list_images`, `create_server`, `server_action`, `delete_server` |
| **Network** | `list_networks`, `list_subnets`, `list_floating_ips` |
| **Volumes** | `list_volumes` |
| **Object storage** (S3) | `list_buckets`, `list_objects`, `create_bucket`, `upload_object`, `download_object`, `delete_object` |
| **Billing** | `get_balance`, `get_balance_prediction` |
| **Account** | `list_projects` |

Destructive tools (`delete_server`, `delete_object`) require `confirm=True`; without it
they return a dry-run preview so the agent can show you what *would* happen first.

## How auth maps to Selectel

| Layer | Endpoint | Credential |
|-------|----------|------------|
| OpenStack (servers/networks/volumes) | `cloud.api.selcloud.ru/identity/v3` | IAM **service user** (username + password + account id) → Keystone token |
| Balance / billing | `api.selectel.ru` | account IAM token, or a **static token** (`X-Token`) for detailed reports |
| Projects | `api.selectel.ru/vpc/resell/v2` | same as above |
| S3 object storage | `s3.<pool>.storage.selcloud.ru` | **S3 access key** issued to the service user |

## Setup

1. **Create a service user** in the control panel: Account → Users → Service users.
   Give it the roles you want the agent to have (start with read-only roles, or scope
   it to a single project).
2. **Issue an S3 key** to that service user (Service users → Access → S3 keys) if you
   want object-storage access.
3. *(Optional)* Create a **static token** (Profile → Access → API keys) for billing
   reports/transactions.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
cp .env.example .env   # then fill in credentials
```

Fill `.env`:

```ini
SEL_ACCOUNT_ID=123456          # domain name, top-right in the control panel
SEL_USERNAME=mcp-agent         # service user
SEL_PASSWORD=...
SEL_PROJECT_ID=<project uuid>  # default project (or discover via list_projects)
SEL_REGION=ru-2
SEL_S3_ACCESS_KEY=...
SEL_S3_SECRET_KEY=...
SEL_STATIC_TOKEN=              # optional
```

## Run / connect to Claude Code

```bash
# from this directory
claude mcp add selectel -- /absolute/path/to/.venv/bin/python -m selectel_mcp
```

Or run it directly over stdio:

```bash
.venv/bin/python -m selectel_mcp
```

For Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "selectel": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "selectel_mcp"]
    }
  }
}
```

The server reads credentials from `.env` in its working directory (or from real
environment variables).

## Safety notes

- The service user is the blast radius — scope its IAM roles to exactly what you want
  the agent to touch. Read-only roles make the whole server read-only.
- `.env` holds secrets and is git-ignored. Don't commit it.
- For infrastructure *changes*, consider managing them with Terraform (provider
  `selectel/selectel`) so every change goes through a reviewable `plan` → `apply`.
  This MCP server is best for queries and quick actions.
