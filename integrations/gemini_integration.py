"""Gemini integration.

Lightweight wrapper around Google's Generative Language API.  Only chat is
implemented for now; throughput is similar to OpenAI and we intentionally keep
this simple since the bulk of the system uses :class:`tools.llm_tool.LLMTool`
for higher-level operations.

Requires ``GEMINI_API_KEY`` to be set; returns a descriptive error dict when the
key is absent so callers can degrade gracefully.
"""

from __future__ import annotations

import logging
import os
import asyncio
from typing import Any

import httpx

from integrations.base_integration import BaseIntegration

logger = logging.getLogger(__name__)


class GeminiIntegration(BaseIntegration):
    name = "gemini"
    description = "Text responses via Google Gemini (Generative Language API)"
    service = "GoogleGemini"
    version = "0.1.0"
    enabled = bool(os.getenv("GEMINI_API_KEY"))

    async def call(self, action: str, payload: Any = None) -> Any:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set GEMINI_API_KEY to enable Gemini integration."}

        if action != "chat":
            return {"integration": self.name, "action": action, "status": "error",
                    "message": f"Unknown action '{action}'. Only 'chat' is supported."}

        p = payload or {}
        messages = p.get("messages") or [{"role": "user", "content": str(p.get("prompt", ""))}]
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        model = p.get("model", "text-bison-001")
        url = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generate"
        headers = {"Authorization": f"Bearer {api_key}"}
        body = {"prompt": {"text": text}, "temperature": 0.7}

        async def _do_call():
            async with httpx.AsyncClient(timeout=None) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                return resp.json()

        try:
            data = await _do_call()
        except Exception as exc:
            # if rate limited, try once more after brief backoff
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None and exc.response.status_code == 429:
                logger.warning("GeminiIntegration received 429, retrying after 1s")
                await asyncio.sleep(1)
                try:
                    data = await _do_call()
                except Exception as exc2:
                    logger.exception("Gemini integration error on retry for action '%s'", action)
                    return {"integration": self.name, "action": action, "status": "error", "message": str(exc2)}
            else:
                logger.exception("Gemini integration error for action '%s'", action)
                return {"integration": self.name, "action": action, "status": "error", "message": str(exc)}

        candidates = data.get("candidates") or []
        content = candidates[0].get("output", "") if candidates else ""
        return {"integration": self.name, "action": action, "status": "ok",
                "content": content, "model": model}

    async def health_check(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))
