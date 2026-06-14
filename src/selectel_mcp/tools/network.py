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
