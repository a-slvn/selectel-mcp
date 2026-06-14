"""High-level deploy flow — one call to stand up a Dockerized app, one to tear it down.

deploy_docker_app provisions: a security group (opening the requested ports), a cloud
server that boots, installs Docker via cloud-init, clones the repo and runs it, and a
floating IP for public access. Resources are tagged with metadata ``mcp-app=<name>`` so
destroy_app can find and remove everything later.
"""

from __future__ import annotations

from .compute import _server_summary

APP_TAG = "mcp-app"


def _cloud_init(git_repo: str | None, run_cmd: str | None) -> str:
    lines = [
        "#cloud-config",
        "package_update: true",
        "packages:",
        "  - git",
        "runcmd:",
        "  - curl -fsSL https://get.docker.com | sh",
        "  - systemctl enable --now docker",
    ]
    if git_repo:
        lines.append(f"  - git clone {git_repo} /opt/app")
    if run_cmd:
        lines.append(f"  - bash -lc 'cd /opt/app 2>/dev/null || true; {run_cmd}'")
    elif git_repo:
        lines.append("  - bash -lc 'cd /opt/app && (docker compose up -d || docker-compose up -d)'")
    return "\n".join(lines) + "\n"


def _pick_network(conn, network: str | None):
    if network:
        return network
    internal = next((n for n in conn.network.networks() if not n.is_router_external), None)
    if internal is None:
        raise RuntimeError("No internal network found; pass network explicitly.")
    return internal.id


def register(mcp, clients) -> None:
    @mcp.tool()
    def deploy_docker_app(
        name: str,
        image: str,
        flavor: str,
        git_repo: str | None = None,
        run_cmd: str | None = None,
        ports: list[int] | None = None,
        volume_size_gb: int = 20,
        network: str | None = None,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Deploy a Dockerized app end-to-end.

        Creates a security group (opening `ports`, default [22, 80, 443]), a server that
        installs Docker + clones `git_repo` + runs it (via cloud-init), and a public IP.
        PAID (server + floating IP) — pass confirm=True to actually provision. Without
        confirm, returns a dry-run plan. Tear down later with destroy_app(name).
        """
        ports = ports or [22, 80, 443]
        user_data = _cloud_init(git_repo, run_cmd)
        sg_name = f"{name}-sg"

        if not confirm:
            return {
                "plan": {
                    "server": {"name": name, "image": image, "flavor": flavor,
                               "volume_size_gb": volume_size_gb},
                    "security_group": {"name": sg_name, "open_ports": ports},
                    "floating_ip": "1 (paid)",
                    "cloud_init": user_data,
                },
                "note": "PAID resources. Re-run with confirm=True to provision.",
            }

        conn = clients.openstack(region=region, project_id=project_id)
        net = _pick_network(conn, network)

        # 1. security group + ingress rules
        sg = conn.network.create_security_group(name=sg_name, description=f"selectel-mcp: {name}")
        for port in ports:
            conn.network.create_security_group_rule(
                security_group_id=sg.id, direction="ingress", ethertype="IPv4",
                protocol="tcp", port_range_min=port, port_range_max=port,
                remote_ip_prefix="0.0.0.0/0",
            )

        # 2. server with cloud-init + public IP, tagged for teardown
        server = conn.create_server(
            name=name, image=image, flavor=flavor, network=[net],
            key_name=clients.settings.keypair_name, security_groups=[sg_name],
            userdata=user_data, auto_ip=True, boot_from_volume=True,
            volume_size=volume_size_gb, terminate_volume=True,
            meta={"managed-by": "selectel-mcp", APP_TAG: name},
            wait=True, timeout=600,
        )
        public_ip = getattr(server, "access_ipv4", None) or getattr(server, "public_v4", None)
        return {
            "app": name,
            "server": _server_summary(server),
            "security_group": {"name": sg_name, "open_ports": ports},
            "public_ip": public_ip,
            "ssh": f"ssh -i .ssh/selectel_mcp root@{public_ip}" if public_ip else None,
            "note": "Server is ACTIVE; Docker install + app start finish in the "
                    "background (~1-3 min). Check via SSH or the exposed port.",
        }

    @mcp.tool()
    def destroy_app(
        name: str,
        confirm: bool = False,
        region: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Tear down everything deploy_docker_app created for `name` (server + its
        floating IP + security group). DESTRUCTIVE — pass confirm=True."""
        conn = clients.openstack(region=region, project_id=project_id)
        servers = [
            s for s in conn.compute.servers(details=True)
            if (s.metadata or {}).get(APP_TAG) == name
        ]
        sg = next(
            (g for g in conn.network.security_groups() if g.name == f"{name}-sg"), None
        )
        if not confirm:
            return {
                "would_delete": {
                    "servers": [{"id": s.id, "name": s.name} for s in servers],
                    "security_group": f"{name}-sg" if sg else None,
                },
                "note": "Re-run with confirm=True to delete. Floating IPs are released "
                        "with their servers.",
            }
        for s in servers:
            conn.delete_server(s.id, wait=True, delete_ips=True)
        if sg is not None:
            conn.network.delete_security_group(sg.id)
        return {
            "app": name,
            "deleted_servers": [s.id for s in servers],
            "deleted_security_group": f"{name}-sg" if sg else None,
            "status": "destroyed",
        }
