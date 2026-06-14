"""Network tools — networks, subnets, floating IPs."""

from __future__ import annotations


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_networks(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List networks in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": n.id,
                "name": n.name,
                "status": n.status,
                "subnet_ids": n.subnet_ids,
                "is_router_external": getattr(n, "is_router_external", None),
            }
            for n in conn.network.networks()
        ]

    @mcp.tool()
    def list_subnets(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List subnets in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": s.id,
                "name": s.name,
                "cidr": s.cidr,
                "network_id": s.network_id,
                "gateway_ip": s.gateway_ip,
                "ip_version": s.ip_version,
            }
            for s in conn.network.subnets()
        ]

    @mcp.tool()
    def list_floating_ips(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List floating (public) IP addresses in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {
                "id": ip.id,
                "floating_ip": ip.floating_ip_address,
                "fixed_ip": ip.fixed_ip_address,
                "status": ip.status,
                "port_id": ip.port_id,
            }
            for ip in conn.network.ips()
        ]

    @mcp.tool()
    def create_floating_ip(region: str | None = None, project_id: str | None = None) -> dict:
        """Allocate a new floating (public) IP from the external network. NOTE: a public
        IP is a paid resource on Selectel."""
        conn = clients.openstack(region=region, project_id=project_id)
        ext = next((n for n in conn.network.networks() if n.is_router_external), None)
        if ext is None:
            raise RuntimeError("No external network found in this region.")
        ip = conn.network.create_ip(floating_network_id=ext.id)
        return {"id": ip.id, "floating_ip": ip.floating_ip_address, "status": "allocated"}

    @mcp.tool()
    def attach_floating_ip(
        server_id: str,
        floating_ip: str,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Associate a floating IP address with a server."""
        conn = clients.openstack(region=region, project_id=project_id)
        server = conn.compute.get_server(server_id)
        conn.compute.add_floating_ip_to_server(server, floating_ip)
        return {"server_id": server_id, "floating_ip": floating_ip, "status": "attached"}

    @mcp.tool()
    def release_floating_ip(
        floating_ip_id: str,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Release (delete) a floating IP allocation. DESTRUCTIVE — pass confirm=True."""
        if not confirm:
            return {
                "would_release": floating_ip_id,
                "note": "Re-run with confirm=True to release this IP.",
            }
        conn = clients.openstack(region=region, project_id=project_id)
        conn.network.delete_ip(floating_ip_id)
        return {"id": floating_ip_id, "status": "released"}
