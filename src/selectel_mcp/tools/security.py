"""Security group tools — firewall rules controlling inbound/outbound traffic."""

from __future__ import annotations


def _sg_summary(sg) -> dict:
    return {
        "id": sg.id,
        "name": sg.name,
        "description": sg.description,
        "rules": [
            {
                "id": r.get("id"),
                "direction": r.get("direction"),
                "protocol": r.get("protocol"),
                "port_min": r.get("port_range_min"),
                "port_max": r.get("port_range_max"),
                "remote_ip_prefix": r.get("remote_ip_prefix"),
            }
            for r in (sg.security_group_rules or [])
        ],
    }


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_security_groups(
        region: str | None = None, project_id: str | None = None
    ) -> list[dict]:
        """List security groups (firewall rule sets) in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [_sg_summary(sg) for sg in conn.network.security_groups()]

    @mcp.tool()
    def create_security_group(
        name: str,
        description: str = "",
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Create a security group. Comes with default allow-all egress; add ingress
        rules with add_security_group_rule."""
        conn = clients.openstack(region=region, project_id=project_id)
        sg = conn.network.create_security_group(name=name, description=description)
        return _sg_summary(sg)

    @mcp.tool()
    def add_security_group_rule(
        security_group_id: str,
        port: int | None = None,
        protocol: str = "tcp",
        remote_ip_prefix: str = "0.0.0.0/0",
        direction: str = "ingress",
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Add a rule to a security group. port=None opens all ports for the protocol.
        Example: open HTTPS = port 443, protocol tcp."""
        conn = clients.openstack(region=region, project_id=project_id)
        rule = conn.network.create_security_group_rule(
            security_group_id=security_group_id,
            direction=direction,
            ethertype="IPv4",
            protocol=protocol,
            port_range_min=port,
            port_range_max=port,
            remote_ip_prefix=remote_ip_prefix,
        )
        return {
            "id": rule.id,
            "security_group_id": security_group_id,
            "direction": rule.direction,
            "protocol": rule.protocol,
            "port": port,
            "remote_ip_prefix": remote_ip_prefix,
            "status": "added",
        }

    @mcp.tool()
    def delete_security_group(
        security_group_id: str,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Delete a security group. DESTRUCTIVE — pass confirm=True."""
        if not confirm:
            return {
                "would_delete": security_group_id,
                "note": "Re-run with confirm=True to delete.",
            }
        conn = clients.openstack(region=region, project_id=project_id)
        conn.network.delete_security_group(security_group_id)
        return {"id": security_group_id, "status": "deleted"}
