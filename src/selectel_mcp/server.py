"""Entry point: builds the FastMCP server and registers all Selectel tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .clients import SelectelClients
from .config import load_settings
from .tools import account, billing, compute, network, storage_s3, volumes

INSTRUCTIONS = """\
Tools for managing a Selectel cloud account.

- Compute / network / volume tools operate on OpenStack and accept optional
  `region` and `project_id` (default to the configured ones). If no project is
  configured, call `list_projects` first and pass `project_id`.
- `list_buckets` / `list_objects` / object tools use S3 object storage.
- `get_balance` / `get_balance_prediction` report account billing.

Destructive tools (`delete_server`, `delete_object`) require `confirm=True`;
without it they return a dry-run preview. Always show the preview to the user
before confirming.
"""


def build_server() -> FastMCP:
    settings = load_settings()
    clients = SelectelClients(settings)
    mcp = FastMCP("selectel", instructions=INSTRUCTIONS)
    for module in (account, compute, network, volumes, storage_s3, billing):
        module.register(mcp, clients)
    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
