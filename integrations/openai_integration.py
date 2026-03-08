"""OpenAI integration.

Supports ``chat``, ``embed``, and ``moderate`` actions via the OpenAI SDK.
Requires ``OPENAI_API_KEY`` to be set; returns a descriptive error dict
when the key is absent so callers degrade gracefully.
"""

from __future__ import annotations

import logging
import os
import asyncio
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
        # gather API keys for retry-on-rate-limit support
        keys = []
        primary = os.getenv("OPENAI_API_KEY")
        if primary:
            keys.append(primary)
        for extra in os.getenv("OPENAI_API_KEYS", "").split(","):
            extra = extra.strip()
            if extra and extra not in keys:
                keys.append(extra)

        # capture gemini credentials for fallback
        gemini_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "text-bison-001")

        if not keys and not gemini_key:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set OPENAI_API_KEY or GEMINI_API_KEY to enable integration."}

        try:
            import openai
            # try OpenAI keys sequentially until one succeeds or we run out
            last_exc: Exception | None = None
            # default models controlled by environment variables for easy switching
            default_chat = os.getenv("OPENAI_DEFAULT_CHAT_MODEL", "gpt-4o-mini")
            default_embed = os.getenv("OPENAI_DEFAULT_EMBED_MODEL", "text-embedding-3-small")
            default_moderate = os.getenv("OPENAI_DEFAULT_MODERATE_MODEL")

            for idx, api_key in enumerate(keys):
                client = openai.AsyncOpenAI(api_key=api_key)
                try:
                    if action == "chat":
                        p = payload or {}
                        messages = p.get("messages") or [{"role": "user", "content": str(p.get("prompt", ""))}]
                        model = p.get("model") or default_chat
                        resp = await client.chat.completions.create(model=model, messages=messages)
                        return {"integration": self.name, "action": action, "status": "ok",
                                "content": resp.choices[0].message.content,
                                "model": resp.model, "usage": dict(resp.usage)}

                    if action == "embed":
                        p = payload or {}
                        inp = p.get("input", "")
                        model = p.get("model") or default_embed
                        resp = await client.embeddings.create(model=model, input=inp)
                        vectors = [d.embedding for d in resp.data]
                        return {"integration": self.name, "action": action, "status": "ok",
                                "embeddings": vectors, "model": resp.model}

                    if action == "moderate":
                        p = payload or {}
                        model = p.get("model") or default_moderate
                        # most moderation endpoints ignore model but include if given
                        args = {"input": p.get("input", "")}
                        if model:
                            args["model"] = model
                        resp = await client.moderations.create(**args)
                        result = resp.results[0]
                        return {"integration": self.name, "action": action, "status": "ok",
                                "flagged": result.flagged, "categories": dict(result.categories)}

                    return {"integration": self.name, "action": action, "status": "error",
                            "message": f"Unknown action '{action}'. Supported: chat, embed, moderate."}
                except Exception as exc:  # catch rate-limit or other errors
                    last_exc = exc
                    retryable = False
                    # common patterns indicating a rate limit; some SDK errors
                    # expose a code or HTTP response, others are generic.
                    if hasattr(exc, 'code') and str(getattr(exc, 'code')).startswith('rate_limit'):
                        retryable = True
                    elif getattr(exc, 'response', None) is not None and getattr(exc.response, 'status_code', None) == 429:
                        retryable = True
                    elif getattr(exc, 'response', None) is not None and getattr(exc.response, 'status_code', None) == 401:
                        # unauthorized; stop trying future keys and fall back
                        logger.warning("OpenAIIntegration key %s unauthorized, breaking to fallback", idx)
                        break
                    elif "rate limit" in str(exc).lower():
                        retryable = True

                    if retryable:
                        # exponential back‑off before trying next key/fallback
                        delay = min(8, 2 ** idx)
                        logger.warning(
                            "OpenAIIntegration key %s hit rate limit (or 429); sleeping %.1fs before next attempt",
                            idx, delay)
                        await asyncio.sleep(delay)
                        continue
                    raise
            # if we get here and gemini is available, call it as a final fallback
            if gemini_key:
                return await self._gemini_chat(prompt_or_payload=payload or {},
                                               model=gemini_model,
                                               action=action)
            raise last_exc if last_exc else RuntimeError("OpenAI integration failed")
        except Exception as exc:
            logger.exception("OpenAI integration error for action '%s'", action)
            return {"integration": self.name, "action": action, "status": "error", "message": str(exc)}

    async def _gemini_chat(self, prompt_or_payload: dict, model: str, action: str) -> dict:
        """Simple Gemini chat helper; only used as fallback in this integration."""
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Gemini key not configured")
        # only chat is currently supported; other actions forward to OpenAI
        if action != "chat":
            return {"integration": self.name, "action": action, "status": "error",
                    "message": "Gemini fallback only supports chat."}
        messages = prompt_or_payload.get("messages") or [{"role": "user", "content": str(prompt_or_payload.get("prompt", ""))}]
        # construct text prompt concatenating messages
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generate"
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"prompt": {"text": text}, "temperature": 0.7}
        import httpx
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        candidates = data.get("candidates") or []
        content = candidates[0].get("output", "") if candidates else ""
        return {"integration": self.name, "action": action, "status": "ok",
                "content": content, "model": model}

    async def health_check(self) -> bool:
        # considered healthy if either OpenAI or Gemini key is available
        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))
