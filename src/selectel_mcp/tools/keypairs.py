"""SSH keypair tools — register public keys so created servers are reachable."""

from __future__ import annotations


def register(mcp, clients) -> None:
    @mcp.tool()
    def list_keypairs(region: str | None = None, project_id: str | None = None) -> list[dict]:
        """List SSH keypairs registered in the project."""
        conn = clients.openstack(region=region, project_id=project_id)
        return [
            {"name": k.name, "fingerprint": k.fingerprint, "type": getattr(k, "type", None)}
            for k in conn.compute.keypairs()
        ]

    @mcp.tool()
    def import_keypair(
        name: str,
        public_key: str,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Register an existing SSH public key under the given name (idempotent-ish:
        errors if the name already exists). Use the resulting name as key_name when
        creating servers."""
        conn = clients.openstack(region=region, project_id=project_id)
        kp = conn.compute.create_keypair(name=name, public_key=public_key)
        return {"name": kp.name, "fingerprint": kp.fingerprint, "status": "imported"}

    @mcp.tool()
    def delete_keypair(
        name: str,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Delete a registered keypair by name. DESTRUCTIVE — pass confirm=True."""
        if not confirm:
            return {"would_delete": name, "note": "Re-run with confirm=True to delete."}
        conn = clients.openstack(region=region, project_id=project_id)
        conn.delete_keypair(name)
        return {"name": name, "status": "deleted"}
