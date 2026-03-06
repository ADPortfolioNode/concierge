"""Async LLM tool wrapper.

This module provides `LLMTool`, an async, modular wrapper for LLM backends.

Supports two call patterns:
  - `await tool.generate(prompt)`         — collects complete response (batch)
  - `async for token in tool.astream(prompt)` — yields tokens as they arrive (streaming)

Backend: OpenAI Chat Completions HTTP API via `httpx` when `OPENAI_API_KEY` is
set; falls back to a deterministic echo responder for local testing/CI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

# A single persistent async client is reused across calls to avoid the
# per-request TLS handshake overhead (~100 ms on cold connections).
_SHARED_CLIENT: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(timeout=None)  # timeout managed per-call
    return _SHARED_CLIENT


class LLMTool:
    """Async LLM tool.

    Usage (batch):
        tool = LLMTool()
        text = await tool.generate("Summarize X", context="previous results")

    Usage (streaming):
        async for token in tool.astream("Summarize X"):
            print(token, end="", flush=True)
    """

    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 120) -> None:
        self.model = model
        # timeout applies to the time-to-first-token for streaming calls and
        # to the total response time for batch calls.  120 s is generous enough
        # for large responses from slow model tiers.
        self.timeout = timeout
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    def _build_messages(self, prompt: str, context: Optional[str]) -> list:
        if context:
            full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}"
        else:
            full_prompt = prompt
        return [{"role": "user", "content": full_prompt}]

    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate complete response for *prompt* (batch mode).

        Internally collects all streaming tokens so that both callers that need
        the full text and callers that call :meth:`astream` share the same code
        path.  Falls back to echo when no API key is configured.
        """
        tokens: list[str] = []
        async for token in self.astream(prompt, context=context):
            tokens.append(token)
        return "".join(tokens)

    async def astream(self, prompt: str, context: Optional[str] = None) -> AsyncIterator[str]:
        """Yield response tokens one-by-one as they arrive from the API.

        Falls back to yielding the full echo string in one shot when no API key
        is configured so callers work identically against the stub.
        """
        messages = self._build_messages(prompt, context)

        if not self._api_key:
            logger.debug("LLMTool no API key; streaming deterministic fallback")
            await asyncio.sleep(0)
            yield f"[LLM-Fallback] {messages[0]['content']}"
            return

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "stream": True,
        }

        client = _get_client()
        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            ) as resp:
                resp.raise_for_status()
                async for raw_line in resp.aiter_lines():
                    if not raw_line or not raw_line.startswith("data: "):
                        continue
                    data_str = raw_line[6:]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_str)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.HTTPError as exc:
            logger.exception("LLMTool HTTP error: %s", exc)
            yield f"[LLM-Error] {exc}"
        except Exception as exc:
            logger.exception("LLMTool unexpected error: %s", exc)
            yield f"[LLM-Error] {exc}"

    # Backwards-compat alias used by some agent subclasses
    async def arun(self, prompt: str, context: Optional[str] = None) -> str:
        return await self.generate(prompt, context=context)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        tool = LLMTool()
        out = await tool.generate("Write a short haiku about coffee.")
        print(out)

    asyncio.run(_demo())
