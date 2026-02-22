"""Async LLM tool wrapper.

This module provides `LLMTool`, an async, modular wrapper intended to be
swapped for different LLM backends. By default it will attempt to call
OpenAI's Chat Completions HTTP API via `httpx` if `OPENAI_API_KEY` is set.
If not configured it falls back to a simple deterministic echo responder
useful for local testing.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class LLMTool:
    """Async LLM tool.

    Usage:
        tool = LLMTool()
        text = await tool.generate("Summarize X", context="previous results")
    """

    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 20) -> None:
        self.model = model
        self.timeout = timeout
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate text for `prompt` optionally using `context`.

        Falls back to an echo when no API key is configured.
        """
        if context:
            full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}"
        else:
            full_prompt = prompt

        if not self._api_key:
            # Local deterministic fallback
            logger.debug("LLMTool no API key; returning deterministic fallback")
            await asyncio.sleep(0)  # keep async
            return f"[LLM-Fallback] {full_prompt}"

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 512,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # extract text from response structure
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                return data.get("text", "")
            except httpx.HTTPError as exc:
                logger.exception("LLMTool HTTP error: %s", exc)
                return f"[LLM-Error] {str(exc)}"
            except Exception as exc:
                logger.exception("LLMTool unexpected error: %s", exc)
                return f"[LLM-Error] {str(exc)}"


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        tool = LLMTool()
        out = await tool.generate("Write a short haiku about coffee.")
        print(out)

    asyncio.run(_demo())
