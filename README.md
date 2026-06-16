# selectel-mcp

An [MCP](https://modelcontextprotocol.io) server that gives an AI agent (Claude Code,
Claude Desktop, etc.) controlled access to a [Selectel](https://selectel.ru) cloud
account: OpenStack cloud servers, S3 object storage, and account billing.

> **Unofficial.** Community project — not affiliated with, endorsed by, or supported
> by Selectel. It talks to the public Selectel/OpenStack APIs with credentials you
> provide. Use at your own risk; you are responsible for any resources it creates and
> any charges they incur.

## What it can do

| Area | Tools |
|------|-------|
| **Deploy** (one-shot) | `deploy_docker_app`, `destroy_app` |
| **Compute** (OpenStack) | `list_servers`, `get_server`, `list_flavors`, `list_images`, `create_server`, `server_action`, `delete_server` |
| **Keypairs** | `list_keypairs`, `import_keypair`, `delete_keypair` |
| **Security groups** | `list_security_groups`, `create_security_group`, `add_security_group_rule`, `delete_security_group` |
| **Network** | `list_networks`, `list_subnets`, `list_floating_ips`, `create_floating_ip`, `attach_floating_ip`, `release_floating_ip` |
| **Volumes** | `list_volumes`, `create_volume`, `attach_volume`, `delete_volume` |
| **Object storage** (S3) | `list_buckets`, `list_objects`, `create_bucket`, `upload_object`, `download_object`, `delete_object` |
| **Billing** | `get_balance`, `get_balance_prediction` |
| **Account** | `list_projects` |

Paid tools (`create_server`, `deploy_docker_app`, `create_floating_ip`) and destructive
tools (`delete_*`, `destroy_app`, `release_floating_ip`) are gated: the destructive ones
require `confirm=True` and otherwise return a dry-run preview, so the agent can show you
what *would* happen first.

### Deploy an app in one call

```
deploy_docker_app(
  name="myapp",
  image="Ubuntu 22.04",
  flavor="SL1.1-1024",
  git_repo="https://github.com/you/myapp",   # cloned to /opt/app, `docker compose up -d`
  ports=[22, 80, 443],
  confirm=True,                               # paid: provisions a server + public IP
)
# → creates a security group, a cloud-init server that installs Docker and runs your
#   repo, and a floating IP. destroy_app("myapp") removes it all later.
```

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

## Development

```bash
pip install -e ".[dev]"   # installs ruff + pytest
ruff check .
pytest
```

The pure helpers (cloud-init rendering, server summarization, public-IP picking) are
unit-tested without touching the network. CI runs lint + tests on every push.

## Safety notes

- The service user is the blast radius — scope its IAM roles to exactly what you want
  the agent to touch. Read-only roles make the whole server read-only.
- `deploy_docker_app` opens the requested ports to `0.0.0.0/0` — the whole internet —
  **including SSH (22)** by default. Pass a narrower `ports` list, or tighten the
  security group afterward, for anything beyond a quick throwaway test.
- `.env` holds secrets and is git-ignored. Don't commit it.
- For infrastructure *changes*, consider managing them with Terraform (provider
  `selectel/selectel`) so every change goes through a reviewable `plan` → `apply`.
  This MCP server is best for queries and quick actions.
