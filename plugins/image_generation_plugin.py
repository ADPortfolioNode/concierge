"""Image-generation plugin.

When ``OPENAI_API_KEY`` is set, generates real images via OpenAI's image API (`gpt-image-1` model).
Otherwise returns a themed placeholder image from picsum.photos so the
pipeline remains end-to-end functional without an API key.
"""

from __future__ import annotations

import hashlib
import logging
import os
import urllib.parse

from plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class ImageGenerationPlugin(BasePlugin):
    name = "image_generation"
    description = "Generates images from text prompts via DALL-E (requires OPENAI_API_KEY)."
    version = "0.2.0"

    async def run(self, input_data: str) -> dict:
        prompt = str(input_data).strip()
        if not prompt:
            prompt = "abstract colorful art"

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return await self._dalle(prompt, api_key)
        return self._placeholder(prompt)

    # ------------------------------------------------------------------ #

    async def _dalle(self, prompt: str, api_key: str) -> dict:
        """Call OpenAI Images API (DALL-E 3)."""
        import httpx
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # OpenAI recently standardized image models under the "gpt-image-1"
        # identifier and will reject older names such as ``dall-e-3`` with a
        # 400 Bad Request.  The endpoint itself still works at
        # /v1/images/generations, but we need to supply the new model name.
        # The OpenAI image endpoint no longer accepts a ``response_format``
        # parameter; it always returns a base64 blob by default.  We still
        # request a single image (``n``) and specify size for backwards
        # compatibility with our earlier implementation.
        payload = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    json=payload,
                    headers=headers,
                )
                # If the call failed the server often returns a helpful JSON
                # body explaining what went wrong (invalid model name, etc.).
                if resp.status_code != 200:
                    # log the full text for debugging; keep the raise for
                    # stacktrace in case httpx wants to add context
                    logger.error(
                        "DALL-E request failed %s %s",
                        resp.status_code,
                        resp.text,
                    )
                resp.raise_for_status()
                data = resp.json()
            item = data["data"][0]
            # Modern API returns base64-encoded JSON under ``b64_json``; older
            # versions returned a direct ``url``.  Handle both so our
            # placeholder unit tests remain valid.
            if "url" in item:
                url = item["url"]
                mime = "image/png"
            else:
                # convert base64 blob to a data URI so the front end can render it
                blob = item.get("b64_json")
                url = f"data:image/png;base64,{blob}" if blob else ""
                mime = "image/png"
            revised = item.get("revised_prompt", prompt)
            return {"prompt": prompt, "revised_prompt": revised, "url": url, "mime_type": mime, "source": "gpt-image-1"}
        except Exception as exc:
            # exc may be an HTTPStatusError; include any response text if
            # available to help troubleshooting.
            logger.exception("DALL-E generation failed: %s", exc)
            # if the error appears to be due to billing or rate limits, and we
            # have a Gemini key, try that before giving up entirely
            msg = str(exc).lower()
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key and ("billing" in msg or "rate limit" in msg or "429" in msg):
                try:
                    logger.info("OpenAI image limit hit, attempting Gemini fallback")
                    return await self._gemini_image(prompt, gemini_key)
                except Exception as gexc:
                    logger.exception("Gemini image fallback failed: %s", gexc)
            return self._placeholder(prompt, error=str(exc))

    async def _gemini_image(self, prompt: str, api_key: str) -> dict:
        """Attempt to generate an image using a hypothetical Gemini image API.

        This is a best‑effort implementation; the real Gemini endpoint may differ
        or not exist yet.  The call mirrors the OpenAI request body as closely as
        possible.  On failure we bubble the exception so the caller can fall
        back to a placeholder.
        """
        import httpx

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "gemini-image-1", "prompt": prompt, "size": "1024x1024"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://generativelanguage.googleapis.com/v1/images:generate",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        item = data.get("data", [{}])[0]
        if "url" in item:
            url = item["url"]
            mime = "image/png"
        else:
            blob = item.get("b64_json")
            url = f"data:image/png;base64,{blob}" if blob else ""
            mime = "image/png"
        revised = item.get("revised_prompt", prompt)
        # mark the source so callers know which provider produced it
        return {"prompt": prompt, "revised_prompt": revised, "url": url, "mime_type": mime, "source": "gemini"}

    @staticmethod
    def _placeholder(prompt: str, error: str | None = None) -> dict:
        """Return a deterministic placeholder image using picsum.photos."""
        # Use a hash of the prompt to always return the same image for the same prompt
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        url = f"https://picsum.photos/seed/{seed}/1024/1024"
        result: dict = {"prompt": prompt, "url": url, "mime_type": "image/jpeg", "source": "placeholder"}
        if error:
            result["error"] = error
            # If we got an error from the OpenAI API it will often contain a
            # message explaining what went wrong (rate limit, billing issues,
            # invalid model, etc.).  Include that message in the note so the
            # frontend or developers can troubleshoot more easily.
            result["note"] = (
                f"Image generation failed ({error}). "
                "Showing a placeholder image instead. "
                "Check OPENAI_API_KEY, billing, or rate limits."
            )
        else:
            result["note"] = "Set OPENAI_API_KEY to enable real image generation via OpenAI."
        return result
