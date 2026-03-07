"""Stripe integration.

Supports ``create_customer``, ``create_payment_intent``, ``list_customers``,
and ``retrieve_customer`` actions via Stripe's REST API.
Requires ``STRIPE_SECRET_KEY`` to be set.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)

_STRIPE_BASE = "https://api.stripe.com/v1"


class StripeIntegration(BaseIntegration):
    name = "stripe"
    description = "Payment processing, subscriptions, and billing via Stripe."
    service = "Stripe"
    version = "0.2.0"
    enabled = bool(os.getenv("STRIPE_SECRET_KEY"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Dispatch to Stripe REST API based on *action*.

        Supported actions:
          ``create_customer``       — payload: {"email": str, "name": str (opt)}
          ``retrieve_customer``     — payload: {"customer_id": str}
          ``list_customers``        — payload: {"limit": int (opt, default 10)}
          ``create_payment_intent`` — payload: {"amount": int (cents), "currency": str, "customer": str (opt)}
        """
        secret = os.getenv("STRIPE_SECRET_KEY")
        if not secret:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set STRIPE_SECRET_KEY to enable Stripe integration."}

        p = payload or {}
        auth = (secret, "")  # Stripe uses HTTP Basic with key as username

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                if action == "create_customer":
                    data = {"email": p["email"]}
                    if p.get("name"):
                        data["name"] = p["name"]
                    resp = await client.post(f"{_STRIPE_BASE}/customers", data=data, auth=auth)

                elif action == "retrieve_customer":
                    cid = p["customer_id"]
                    resp = await client.get(f"{_STRIPE_BASE}/customers/{cid}", auth=auth)

                elif action == "list_customers":
                    limit = int(p.get("limit", 10))
                    resp = await client.get(f"{_STRIPE_BASE}/customers", params={"limit": limit}, auth=auth)

                elif action == "create_payment_intent":
                    data = {"amount": str(p["amount"]), "currency": p.get("currency", "usd")}
                    if p.get("customer"):
                        data["customer"] = p["customer"]
                    resp = await client.post(f"{_STRIPE_BASE}/payment_intents", data=data, auth=auth)

                else:
                    return {"integration": self.name, "action": action, "status": "error",
                            "message": f"Unknown action '{action}'. Supported: create_customer, retrieve_customer, list_customers, create_payment_intent."}

            result = resp.json()
            if resp.status_code >= 400:
                return {"integration": self.name, "action": action, "status": "error",
                        "http_status": resp.status_code, "stripe_error": result.get("error", result)}
            return {"integration": self.name, "action": action, "status": "ok", "data": result}

        except Exception as exc:
            logger.exception("Stripe integration error for action '%s'", action)
            return {"integration": self.name, "action": action, "status": "error", "message": str(exc)}

    async def health_check(self) -> bool:
        return bool(os.getenv("STRIPE_SECRET_KEY"))
