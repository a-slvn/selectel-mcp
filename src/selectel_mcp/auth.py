"""Authentication + REST client for the Selectel account/billing API (api.selectel.ru).

Two auth modes are supported, picked automatically:
  * Static token (``X-Token``) — used if SEL_STATIC_TOKEN is set. Required for
    detailed billing reports / transactions.
  * Account-scoped IAM token (``X-Auth-Token``) — minted from the service-user
    password against Keystone, cached until shortly before expiry. Works for
    balance, IAM and other account-scoped endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .config import Settings

# Refresh the IAM token this long before it actually expires.
_TOKEN_SKEW = timedelta(minutes=5)


class SelectelRest:
    """Thin REST client over the Selectel account/billing API."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._client = httpx.Client(base_url=settings.api_base, timeout=30.0)
        self._iam_token: str | None = None
        self._iam_expires: datetime | None = None

    # -- token management -----------------------------------------------------
    def _mint_account_iam_token(self) -> tuple[str, datetime]:
        """Get a domain(account)-scoped Keystone token for the service user."""
        body = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self._s.username,
                            "domain": {"name": self._s.account_id},
                            "password": self._s.password,
                        }
                    },
                },
                "scope": {"domain": {"name": self._s.account_id}},
            }
        }
        resp = httpx.post(
            f"{self._s.auth_url}/auth/tokens", json=body, timeout=30.0
        )
        resp.raise_for_status()
        token = resp.headers["X-Subject-Token"]
        expires_raw = resp.json()["token"]["expires_at"]
        expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        return token, expires

    def _account_iam_token(self) -> str:
        now = datetime.now(timezone.utc)
        if (
            self._iam_token is None
            or self._iam_expires is None
            or now >= self._iam_expires - _TOKEN_SKEW
        ):
            self._iam_token, self._iam_expires = self._mint_account_iam_token()
        return self._iam_token

    def _auth_headers(self) -> dict[str, str]:
        if self._s.static_token:
            return {"X-Token": self._s.static_token}
        return {"X-Auth-Token": self._account_iam_token()}

    # -- requests -------------------------------------------------------------
    def get(self, path: str, **kwargs) -> httpx.Response:
        resp = self._client.get(path, headers=self._auth_headers(), **kwargs)
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self._client.close()
