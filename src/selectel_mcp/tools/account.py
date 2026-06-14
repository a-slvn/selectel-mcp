"""Account tools — projects (helps discover project_id for OpenStack scoping)."""

from __future__ import annotations


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_projects() -> list[dict]:
        """List Cloud Platform projects. Use a project's id as project_id for OpenStack tools."""
        resp = clients.rest.get("/vpc/resell/v2/projects")
        data = resp.json()
        projects = data.get("projects", data) if isinstance(data, dict) else data
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "enabled": p.get("enabled"),
                "url": p.get("url"),
            }
            for p in projects
        ]
