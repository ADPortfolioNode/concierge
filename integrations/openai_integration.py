"""OpenAI integration.

Supports ``chat``, ``embed``, and ``moderate`` actions via the OpenAI SDK.
Requires ``OPENAI_API_KEY`` to be set; returns a descriptive error dict
when the key is absent so callers degrade gracefully.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)


class OpenAIIntegration(BaseIntegration):
    name = "openai"
    description = "Language model completions and embeddings via the OpenAI API."
    service = "OpenAI"
    version = "0.2.0"
    enabled = bool(os.getenv("OPENAI_API_KEY"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Dispatch to OpenAI API based on *action*.

        Supported actions:
          ``chat``     — payload: {"messages": [...], "model": str (optional)}
          ``embed``    — payload: {"input": str | list[str], "model": str (optional)}
          ``moderate`` — payload: {"input": str}
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set OPENAI_API_KEY to enable OpenAI integration."}

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)

            if action == "chat":
                p = payload or {}
                messages = p.get("messages") or [{"role": "user", "content": str(p.get("prompt", ""))}]
                model = p.get("model", "gpt-4o-mini")
                resp = await client.chat.completions.create(model=model, messages=messages)
                return {"integration": self.name, "action": action, "status": "ok",
                        "content": resp.choices[0].message.content,
                        "model": resp.model, "usage": dict(resp.usage)}

            if action == "embed":
                p = payload or {}
                inp = p.get("input", "")
                model = p.get("model", "text-embedding-3-small")
                resp = await client.embeddings.create(model=model, input=inp)
                vectors = [d.embedding for d in resp.data]
                return {"integration": self.name, "action": action, "status": "ok",
                        "embeddings": vectors, "model": resp.model}

            if action == "moderate":
                p = payload or {}
                resp = await client.moderations.create(input=p.get("input", ""))
                result = resp.results[0]
                return {"integration": self.name, "action": action, "status": "ok",
                        "flagged": result.flagged, "categories": dict(result.categories)}

            return {"integration": self.name, "action": action, "status": "error",
                    "message": f"Unknown action '{action}'. Supported: chat, embed, moderate."}

        except Exception as exc:
            logger.exception("OpenAI integration error for action '%s'", action)
            return {"integration": self.name, "action": action, "status": "error", "message": str(exc)}

    async def health_check(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
