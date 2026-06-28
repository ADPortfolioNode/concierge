"""OpenAI integration.

Supports ``chat``, ``embed``, and ``moderate`` actions via the OpenAI SDK.
Uses Replit AI Integrations (AI_INTEGRATIONS_OPENAI_API_KEY) when available,
falling back to OPENAI_API_KEY. Returns a descriptive error dict when no key
is configured so callers degrade gracefully.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any

from integrations.base_integration import BaseIntegration
from config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_openai_api_key() -> str:
    """Return the best available OpenAI API key.

    Values are centralized in config/settings (key literals only appear in settings.py).
    """
    settings = get_settings()
    return settings.openai_api_key or ""


def _get_openai_base_url() -> str | None:
    """Return the OpenAI-compatible base URL (from settings)."""
    settings = get_settings()
    # settings already prefers AI_INTEGRATIONS_ variants
    base = settings.openai_api_base
    return base if base and base != "https://api.openai.com/v1" else None


class OpenAIIntegration(BaseIntegration):
    name = "openai"
    description = "Language model completions and embeddings via the OpenAI API."
    service = "OpenAI"
    version = "0.2.0"

    @property
    def enabled(self) -> bool:  # type: ignore[override]
        return bool(_get_openai_api_key())

    async def call(self, action: str, payload: Any = None) -> Any:
        """Dispatch to OpenAI API based on *action*.

        Supported actions:
          ``chat``     — payload: {"messages": [...], "model": str (optional)}
          ``embed``    — payload: {"input": str | list[str], "model": str (optional)}
          ``moderate`` — payload: {"input": str}
        """
        settings = get_settings()

        # gather API keys for retry-on-rate-limit support
        keys = []
        primary = _get_openai_api_key()
        if primary:
            keys.append(primary)
        for extra in (settings.openai_api_keys or "").split(","):
            extra = extra.strip()
            if extra and extra not in keys:
                keys.append(extra)

        # capture gemini credentials for fallback
        gemini_key = settings.gemini_api_key
        gemini_model = settings.gemini_model

        if not keys and not gemini_key:
            return {"integration": self.name, "action": action, "status": "unconfigured",
                    "message": "Set AI_INTEGRATIONS_OPENAI_API_KEY or OPENAI_API_KEY to enable integration."}

        # attempt to use OpenAI SDK; fall back to Gemini on ANY failure
        try:
            import openai
        except Exception as import_exc:  # SDK not present or import failed
            logger.warning("OpenAI SDK import failed: %s; will try Gemini if available", import_exc)
            if gemini_key:
                return await self._gemini_chat(prompt_or_payload=payload or {},
                                               model=gemini_model,
                                               action=action)
            return {"integration": self.name, "action": action, "status": "error", "message": str(import_exc)}

        last_exc: Exception | None = None
        # default models from centralized settings (env key strings only in settings.py)
        default_chat = settings.openai_default_chat_model
        default_embed = settings.openai_default_embed_model
        default_moderate = settings.openai_default_moderate_model or None

        base_url = _get_openai_base_url()

        for idx, api_key in enumerate(keys):
            client_kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = openai.AsyncOpenAI(**client_kwargs)
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
                if hasattr(exc, 'code') and str(getattr(exc, 'code')).startswith('rate_limit'):
                    retryable = True
                elif getattr(exc, 'response', None) is not None and getattr(exc.response, 'status_code', None) == 429:
                    retryable = True
                elif getattr(exc, 'response', None) is not None and getattr(exc.response, 'status_code', None) == 401:
                    logger.warning("OpenAIIntegration key %s unauthorized, breaking to fallback", idx)
                    break
                elif "rate limit" in str(exc).lower():
                    retryable = True

                if retryable:
                    delay = min(8, 2 ** idx)
                    logger.warning(
                        "OpenAIIntegration key %s hit rate limit; sleeping %.1fs before next attempt",
                        idx, delay)
                    await asyncio.sleep(delay)
                    continue
                # non-retryable error, break to Gemini if available
                logger.warning("OpenAIIntegration error on key %s: %s; will try Gemini", idx, exc)
                break
        # if we get here and gemini is available, call it as a final fallback
        if gemini_key:
            return await self._gemini_chat(prompt_or_payload=payload or {},
                                           model=gemini_model,
                                           action=action)
        if last_exc:
            raise last_exc
        return {"integration": self.name, "action": action, "status": "error", "message": "OpenAI integration failed"}

    async def _gemini_chat(self, prompt_or_payload: dict, model: str, action: str) -> dict:
        """Simple Gemini chat helper; only used as fallback in this integration."""
        key = get_settings().gemini_api_key
        if not key:
            raise RuntimeError("Gemini key not configured")
        # only chat is currently supported; other actions forward to OpenAI
        if action != "chat":
            return {"integration": self.name, "action": action, "status": "error",
                    "message": "Gemini fallback only supports chat."}
        messages = prompt_or_payload.get("messages") or [{"role": "user", "content": str(prompt_or_payload.get("prompt", ""))}]
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.7}
        }
        import httpx
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        candidates = data.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            content = parts[0].get("text", "") if parts else ""
        else:
            content = ""
        return {"integration": self.name, "action": action, "status": "ok",
                "content": content, "model": model}

    async def health_check(self) -> bool:
        # considered healthy if either OpenAI or Gemini key is available (via settings)
        return bool(_get_openai_api_key() or get_settings().gemini_api_key)
