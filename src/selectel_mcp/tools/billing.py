"""Billing tools — account balance and balance prediction."""

from __future__ import annotations


def register(mcp, clients) -> None:
    @mcp.tool()
    def get_balance() -> dict:
        """Get current account balances (primary, bonus, VK rubles, etc.)."""
        resp = clients.rest.get("/v3/balances")
        return resp.json()

    @mcp.tool()
    def get_balance_prediction() -> dict:
        """Estimate how long the remaining balance will keep services running."""
        resp = clients.rest.get("/v2/billing/prediction")
        return resp.json()
