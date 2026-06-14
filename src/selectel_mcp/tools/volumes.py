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

    @mcp.tool()
    def create_volume(
        name: str,
        size_gb: int,
        volume_type: str | None = None,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Create a new block storage volume (disk)."""
        conn = clients.openstack(region=region, project_id=project_id)
        kwargs = {"name": name, "size": size_gb}
        if volume_type:
            kwargs["volume_type"] = volume_type
        v = conn.block_storage.create_volume(**kwargs)
        return {"id": v.id, "name": v.name, "size_gb": v.size, "status": v.status}

    @mcp.tool()
    def attach_volume(
        server_id: str,
        volume_id: str,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Attach a volume to a server."""
        conn = clients.openstack(region=region, project_id=project_id)
        server = conn.compute.get_server(server_id)
        volume = conn.block_storage.get_volume(volume_id)
        conn.compute.create_volume_attachment(server, volume_id=volume.id)
        return {"server_id": server_id, "volume_id": volume_id, "status": "attached"}

    @mcp.tool()
    def delete_volume(
        volume_id: str,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Delete a volume. DESTRUCTIVE — pass confirm=True."""
        if not confirm:
            return {"would_delete": volume_id, "note": "Re-run with confirm=True to delete."}
        conn = clients.openstack(region=region, project_id=project_id)
        conn.block_storage.delete_volume(volume_id)
        return {"id": volume_id, "status": "deletion_requested"}
