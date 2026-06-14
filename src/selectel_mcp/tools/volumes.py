"""Block storage tools — volumes (disks)."""

from __future__ import annotations


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_volumes(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List block storage volumes (disks) in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": v.id,
                "name": v.name,
                "status": v.status,
                "size_gb": v.size,
                "volume_type": v.volume_type,
                "is_bootable": v.is_bootable,
                "attachments": [
                    {"server_id": a.get("server_id"), "device": a.get("device")}
                    for a in (v.attachments or [])
                ],
            }
            for v in conn.block_storage.volumes(details=True)
        ]
