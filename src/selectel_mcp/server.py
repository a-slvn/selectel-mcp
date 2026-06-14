"""Entry point: builds the FastMCP server and registers all Selectel tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .clients import SelectelClients
from .config import load_settings
from .tools import (
    account,
    billing,
    compute,
    deploy,
    keypairs,
    network,
    security,
    storage_s3,
    volumes,
)

INSTRUCTIONS = """\
Tools for managing a Selectel cloud account.

- Compute / network / volume tools operate on OpenStack and accept optional
  `region` and `project_id` (default to the configured ones). If no project is
  configured, call `list_projects` first and pass `project_id`.
- `list_buckets` / `list_objects` / object tools use S3 object storage.
- `get_balance` / `get_balance_prediction` report account billing.
- To deploy an app fast: `deploy_docker_app` (creates security group + server with
  cloud-init that installs Docker and runs the repo + a public IP). `destroy_app`
  tears it all down. Lower-level building blocks: keypairs, security groups,
  floating IPs, volumes.

Paid/destructive tools (`create_server`, `deploy_docker_app`, `create_floating_ip`,
`delete_server`, `delete_object`, `destroy_app`, …) either cost money or are
irreversible. The destructive ones require `confirm=True` and otherwise return a
dry-run preview — always show it to the user before confirming.
"""


def build_server() -> FastMCP:
    settings = load_settings()
    clients = SelectelClients(settings)
    mcp = FastMCP("selectel", instructions=INSTRUCTIONS)
    for module in (
        account,
        compute,
        keypairs,
        network,
        security,
        volumes,
        storage_s3,
        billing,
        deploy,
    ):
        module.register(mcp, clients)
    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
