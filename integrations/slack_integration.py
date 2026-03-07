"""Slack integration.

Supports ``post_message``, ``list_channels``, and ``get_channel_history``
actions via the Slack Web API. Requires ``SLACK_BOT_TOKEN`` to be set.
Also supports ``webhook_post`` for Incoming Webhook URLs (``SLACK_WEBHOOK_URL``).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)

_SLACK_API = "https://slack.com/api"


class SlackIntegration(BaseIntegration):
    name = "slack"
    description = "Team notifications and bot interactions via Slack."
    service = "Slack"
    version = "0.2.0"
    enabled = bool(os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_WEBHOOK_URL"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Dispatch to Slack API based on *action*.

        Supported actions:
          ``post_message``      — payload: {"channel": str, "text": str, "blocks": list (opt)}
          ``webhook_post``      — payload: {"text": str, "blocks": list (opt)}
          ``list_channels``     — payload: {"limit": int (opt, default 100)}
          ``get_channel_history``— payload: {"channel": str, "limit": int (opt, default 20)}
        """
        token = os.getenv("SLACK_BOT_TOKEN")
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        p = payload or {}

        if not token and not webhook:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set SLACK_BOT_TOKEN or SLACK_WEBHOOK_URL to enable Slack integration."}

        try:
            async with httpx.AsyncClient(timeout=10) as client:

                if action == "webhook_post":
                    if not webhook:
                        return {"integration": self.name, "action": action, "status": "error",
                                "message": "SLACK_WEBHOOK_URL not set."}
                    body: dict = {"text": p.get("text", "")}
                    if p.get("blocks"):
                        body["blocks"] = p["blocks"]
                    resp = await client.post(webhook, json=body)
                    return {"integration": self.name, "action": action,
                            "status": "ok" if resp.text == "ok" else "error", "response": resp.text}

                if not token:
                    return {"integration": self.name, "action": action, "status": "unconfigured",
                            "message": "SLACK_BOT_TOKEN not set. Use webhook_post with SLACK_WEBHOOK_URL instead."}

                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

                if action == "post_message":
                    body = {"channel": p["channel"], "text": p.get("text", "")}
                    if p.get("blocks"):
                        body["blocks"] = p["blocks"]
                    resp = await client.post(f"{_SLACK_API}/chat.postMessage", json=body, headers=headers)

                elif action == "list_channels":
                    params = {"limit": p.get("limit", 100), "exclude_archived": True}
                    resp = await client.get(f"{_SLACK_API}/conversations.list", params=params, headers=headers)

                elif action == "get_channel_history":
                    params = {"channel": p["channel"], "limit": p.get("limit", 20)}
                    resp = await client.get(f"{_SLACK_API}/conversations.history", params=params, headers=headers)

                else:
                    return {"integration": self.name, "action": action, "status": "error",
                            "message": f"Unknown action '{action}'. Supported: post_message, webhook_post, list_channels, get_channel_history."}

            result = resp.json()
            if not result.get("ok"):
                return {"integration": self.name, "action": action, "status": "error",
                        "slack_error": result.get("error", "unknown"), "data": result}
            return {"integration": self.name, "action": action, "status": "ok", "data": result}

        except Exception as exc:
            logger.exception("Slack integration error for action '%s'", action)
            return {"integration": self.name, "action": action, "status": "error", "message": str(exc)}

    async def health_check(self) -> bool:
        return bool(os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_WEBHOOK_URL"))
