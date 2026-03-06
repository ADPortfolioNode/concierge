"""Stripe integration stub.

Replace the ``call`` body with real ``stripe`` SDK calls once the
``STRIPE_SECRET_KEY`` environment variable is available.
"""

from __future__ import annotations

import os
from typing import Any

from integrations.base_integration import BaseIntegration


class StripeIntegration(BaseIntegration):
    name = "stripe"
    description = "Payment processing, subscriptions, and billing via Stripe."
    service = "Stripe"
    version = "0.1.0"
    enabled = bool(os.getenv("STRIPE_SECRET_KEY"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Stub — returns a mock response for every action."""
        return {
            "integration": self.name,
            "action": action,
            "status": "stub",
            "message": (
                "Stripe integration is not yet configured. "
                "Set STRIPE_SECRET_KEY and implement the real call."
            ),
        }

    async def health_check(self) -> bool:
        return bool(os.getenv("STRIPE_SECRET_KEY"))
