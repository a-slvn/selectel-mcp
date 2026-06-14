"""Compute tools — OpenStack cloud servers, flavors, images."""

from __future__ import annotations

from typing import Any


def _server_summary(s: Any) -> dict:
    d = s.to_dict() if hasattr(s, "to_dict") else dict(s)
    flavor = d.get("flavor") or {}
    addresses = d.get("addresses") or {}
    ips = [
        a.get("addr")
        for net in addresses.values()
        for a in net
        if isinstance(a, dict) and a.get("addr")
    ]
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "status": d.get("status"),
        "flavor": flavor.get("original_name") or flavor.get("id"),
        "vcpus": flavor.get("vcpus"),
        "ram_mb": flavor.get("ram"),
        "ips": ips,
        "created_at": d.get("created_at"),
        "power_state": d.get("power_state"),
    }


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_servers(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List cloud servers (OpenStack instances). Defaults to the configured region/project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [_server_summary(s) for s in conn.compute.servers(details=True)]

    @mcp.tool()
    def get_server(
        server_id: str, region: str | None = None, project_id: str | None = None
    ) -> dict:
        """Get full details for one cloud server by id."""
        conn = clients.openstack(region=region, project_id=project_id)
        return conn.compute.get_server(server_id).to_dict()

    @mcp.tool()
    def list_flavors(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List available server flavors (vCPU/RAM/disk configurations)."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": f.id,
                "name": f.name,
                "vcpus": f.vcpus,
                "ram_mb": f.ram,
                "disk_gb": f.disk,
            }
            for f in conn.compute.flavors()
        ]

    @mcp.tool()
    def list_images(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List available OS images for booting servers."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": img.id,
                "name": img.name,
                "status": img.status,
                "min_disk_gb": getattr(img, "min_disk", None),
                "min_ram_mb": getattr(img, "min_ram", None),
                "size_bytes": getattr(img, "size", None),
            }
            for img in conn.image.images()
        ]

    @mcp.tool()
    def create_server(
        name: str,
        image: str,
        flavor: str,
        network: str,
        volume_size_gb: int = 20,
        key_name: str | None = None,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Create a cloud server (boots from a new network volume).

        image/flavor/network accept either a name or an id. Returns the created
        server summary. The server is provisioned asynchronously (does not wait).
        """
        conn = clients.openstack(region=region, project_id=project_id)
        server = conn.create_server(
            name=name,
            image=image,
            flavor=flavor,
            network=[network],
            key_name=key_name,
            boot_from_volume=True,
            volume_size=volume_size_gb,
            terminate_volume=True,
            wait=False,
        )
        return _server_summary(server)

    @mcp.tool()
    def server_action(
        server_id: str,
        action: str,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Power action on a server. action ∈ {start, stop, reboot, reboot_hard}."""
        conn = clients.openstack(region=region, project_id=project_id)
        server = conn.compute.get_server(server_id)
        action = action.lower()
        if action == "start":
            conn.compute.start_server(server)
        elif action == "stop":
            conn.compute.stop_server(server)
        elif action == "reboot":
            conn.compute.reboot_server(server, "SOFT")
        elif action == "reboot_hard":
            conn.compute.reboot_server(server, "HARD")
        else:
            raise ValueError(f"Unknown action {action!r}. Use start|stop|reboot|reboot_hard.")
        return {"server_id": server_id, "action": action, "status": "requested"}

    @mcp.tool()
    def delete_server(
        server_id: str,
        confirm: bool = False,
        delete_volumes: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Delete a cloud server. DESTRUCTIVE — must pass confirm=True to proceed.

        Without confirm, returns a preview of what would be deleted.
        """
        conn = clients.openstack(region=region, project_id=project_id)
        server = conn.compute.get_server(server_id)
        if not confirm:
            return {
                "would_delete": _server_summary(server),
                "delete_volumes": delete_volumes,
                "note": "Re-run with confirm=True to actually delete this server.",
            }
        conn.delete_server(server_id, wait=False, delete_ips=True)
        return {"server_id": server_id, "status": "deletion_requested"}
