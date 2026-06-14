"""Lazily-constructed clients shared by all tools: OpenStack, S3, REST."""

from __future__ import annotations

from typing import Any

from .auth import SelectelRest
from .config import Settings


class SelectelClients:
    """Holds settings and builds/caches the underlying SDK clients on demand."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._os_conns: dict[tuple[str, str], Any] = {}
        self._rest: SelectelRest | None = None
        self._s3: Any | None = None

    # -- OpenStack ------------------------------------------------------------
    def openstack(self, region: str | None = None, project_id: str | None = None):
        """Return an openstacksdk Connection scoped to a region + project (cached)."""
        import openstack  # imported lazily so the package loads without it at rest

        region = region or self.settings.region
        project_id = project_id or self.settings.project_id
        if not project_id:
            raise RuntimeError(
                "No project specified. Set SEL_PROJECT_ID or pass project_id "
                "(list available projects with the list_projects tool)."
            )
        key = (region, project_id)
        if key not in self._os_conns:
            self._os_conns[key] = openstack.connect(
                auth_url=self.settings.auth_url,
                username=self.settings.username,
                password=self.settings.password,
                project_id=project_id,
                user_domain_name=self.settings.account_id,
                project_domain_name=self.settings.account_id,
                region_name=region,
                identity_api_version=3,
                interface="public",
                app_name="selectel-mcp",
            )
        return self._os_conns[key]

    # -- REST (account / billing) --------------------------------------------
    @property
    def rest(self) -> SelectelRest:
        if self._rest is None:
            self._rest = SelectelRest(self.settings)
        return self._rest

    # -- S3 -------------------------------------------------------------------
    def s3(self):
        """Return a boto3 S3 client for Selectel object storage (cached)."""
        if self._s3 is None:
            import boto3
            from botocore.config import Config

            if not self.settings.has_s3:
                raise RuntimeError(
                    "S3 is not configured. Set SEL_S3_ACCESS_KEY / SEL_S3_SECRET_KEY."
                )
            self._s3 = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name=self.settings.s3_region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._s3

    def close(self) -> None:
        if self._rest is not None:
            self._rest.close()
