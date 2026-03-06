"""Slack integration stub.

Replace the ``call`` body with real Slack Bolt / Webhooks calls once the
``SLACK_BOT_TOKEN`` environment variable is available.
"""

from __future__ import annotations

import os
from typing import Any

from integrations.base_integration import BaseIntegration


class SlackIntegration(BaseIntegration):
    name = "slack"
    description = "Team notifications and bot interactions via Slack."
    service = "Slack"
    version = "0.1.0"
    enabled = bool(os.getenv("SLACK_BOT_TOKEN"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Stub — returns a mock response for every action."""
        return {
            "integration": self.name,
            "action": action,
            "status": "stub",
            "message": (
                "Slack integration is not yet configured. "
                "Set SLACK_BOT_TOKEN and implement the real call."
            ),
        }

    async def health_check(self) -> bool:
        return bool(os.getenv("SLACK_BOT_TOKEN"))
