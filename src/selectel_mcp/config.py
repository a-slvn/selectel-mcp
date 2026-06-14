"""Environment-driven configuration for the Selectel MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    # IAM service user (OpenStack + account IAM token)
    account_id: str
    username: str
    password: str
    project_id: str | None
    region: str
    auth_url: str
    keypair_name: str

    # Account / billing REST API
    api_base: str
    static_token: str | None

    # S3 object storage
    s3_access_key: str | None
    s3_secret_key: str | None
    s3_endpoint: str
    s3_region: str

    @property
    def has_s3(self) -> bool:
        return bool(self.s3_access_key and self.s3_secret_key)


def load_settings() -> Settings:
    """Load settings from environment / .env. Raises if core OpenStack creds missing."""
    # Prefer a .env found from the current working directory; fall back to the
    # one at the project root next to this package so the server finds creds no
    # matter which directory the MCP host launches it from. Real env vars win.
    load_dotenv()
    project_env = Path(__file__).resolve().parents[2] / ".env"
    if project_env.is_file():
        load_dotenv(project_env, override=False)
    return Settings(
        account_id=_get("SEL_ACCOUNT_ID", required=True),
        username=_get("SEL_USERNAME", required=True),
        password=_get("SEL_PASSWORD", required=True),
        project_id=_get("SEL_PROJECT_ID") or None,
        region=_get("SEL_REGION", "ru-2"),
        auth_url=_get("SEL_AUTH_URL", "https://cloud.api.selcloud.ru/identity/v3"),
        keypair_name=_get("SEL_KEYPAIR", "selectel-mcp"),
        api_base=_get("SEL_API_BASE", "https://api.selectel.ru").rstrip("/"),
        static_token=_get("SEL_STATIC_TOKEN") or None,
        s3_access_key=_get("SEL_S3_ACCESS_KEY") or None,
        s3_secret_key=_get("SEL_S3_SECRET_KEY") or None,
        s3_endpoint=_get("SEL_S3_ENDPOINT", "https://s3.ru-1.storage.selcloud.ru").rstrip("/"),
        s3_region=_get("SEL_S3_REGION", "ru-1"),
    )
