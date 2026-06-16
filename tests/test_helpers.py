"""Unit tests for the pure helpers — no network or cloud SDKs required."""

from __future__ import annotations

import json

from selectel_mcp.tools.compute import _server_detail, _server_summary
from selectel_mcp.tools.deploy import _cloud_init, _public_ip

# -- _public_ip ---------------------------------------------------------------


def test_public_ip_picks_first_public():
    assert _public_ip(["10.0.0.5", "8.8.8.8", "1.1.1.1"]) == "8.8.8.8"


def test_public_ip_skips_private_and_invalid():
    assert _public_ip(["192.168.1.1", "not-an-ip", "172.16.0.1"]) is None


def test_public_ip_empty():
    assert _public_ip([]) is None


# -- _cloud_init --------------------------------------------------------------


def test_cloud_init_installs_docker():
    out = _cloud_init(None, None)
    assert out.startswith("#cloud-config")
    assert "get.docker.com" in out
    assert out.endswith("\n")


def test_cloud_init_clones_repo_and_defaults_to_compose():
    out = _cloud_init("https://github.com/you/app", None)
    assert "git clone https://github.com/you/app /opt/app" in out
    assert "docker compose up -d" in out


def test_cloud_init_quotes_repo_against_injection():
    out = _cloud_init("https://x/app; rm -rf /", None)
    assert "git clone 'https://x/app; rm -rf /' /opt/app" in out
    assert "git clone https://x/app; rm -rf / /opt/app" not in out


def test_cloud_init_run_cmd_overrides_default_compose():
    out = _cloud_init("https://github.com/you/app", "make deploy")
    assert "make deploy" in out
    assert "docker compose up -d" not in out


def test_cloud_init_body_parses_with_tricky_inputs():
    # An SSH-form repo (embedded ':') and a run_cmd with a quote + ': ' would
    # corrupt a hand-built YAML document. The JSON body must still parse cleanly,
    # and run_cmd must survive verbatim inside the list-form bash invocation.
    out = _cloud_init("git@github.com:org/repo.git", "echo 'done: ok'")
    header, _, body = out.partition("\n")
    assert header == "#cloud-config"
    doc = json.loads(body)  # JSON is valid YAML => unambiguously valid cloud-init
    assert doc["runcmd"][-1] == [
        "bash",
        "-lc",
        "cd /opt/app 2>/dev/null || true; echo 'done: ok'",
    ]
    assert "git clone git@github.com:org/repo.git /opt/app" in doc["runcmd"]


# -- _server_summary / _server_detail -----------------------------------------

_RAW = {
    "id": "srv-1",
    "name": "web",
    "status": "ACTIVE",
    "flavor": {"original_name": "SL1.1-1024", "vcpus": 1, "ram": 1024},
    "addresses": {"net": [{"addr": "10.0.0.4"}, {"addr": "203.0.113.9"}]},
    "created_at": "2026-06-16T00:00:00Z",
    "power_state": 1,
    "image": {"id": "img-1"},
    "key_name": "selectel-mcp",
    "security_groups": [{"name": "web-sg"}],
    "metadata": {"mcp-app": "web"},
    "user_data": "c2VjcmV0",  # must NOT leak into the curated detail view
}


def test_server_summary_extracts_core_fields():
    s = _server_summary(dict(_RAW))
    assert s["id"] == "srv-1"
    assert s["flavor"] == "SL1.1-1024"
    assert s["vcpus"] == 1
    assert s["ram_mb"] == 1024
    assert s["ips"] == ["10.0.0.4", "203.0.113.9"]


def test_server_summary_handles_missing_flavor_and_addresses():
    s = _server_summary({"id": "x"})
    assert s["id"] == "x"
    assert s["ips"] == []
    assert s["flavor"] is None


def test_server_summary_ignores_nonlist_address_values():
    # A network whose value is null/scalar (seen in transitional states) must not
    # crash IP extraction.
    s = _server_summary({"addresses": {"net": None, "ext": [{"addr": "1.2.3.4"}]}})
    assert s["ips"] == ["1.2.3.4"]


def test_server_detail_adds_fields_and_omits_user_data():
    d = _server_detail(dict(_RAW))
    assert d["image"] == "img-1"
    assert d["key_name"] == "selectel-mcp"
    assert d["security_groups"] == ["web-sg"]
    assert d["metadata"] == {"mcp-app": "web"}
    assert "user_data" not in d
