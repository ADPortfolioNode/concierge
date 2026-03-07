"""Image-generation plugin.

When ``OPENAI_API_KEY`` is set, generates real images via OpenAI DALL-E 3.
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
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            url = data["data"][0]["url"]
            revised = data["data"][0].get("revised_prompt", prompt)
            return {"prompt": prompt, "revised_prompt": revised, "url": url, "mime_type": "image/png", "source": "dall-e-3"}
        except Exception as exc:
            logger.exception("DALL-E generation failed: %s", exc)
            return self._placeholder(prompt, error=str(exc))

    @staticmethod
    def _placeholder(prompt: str, error: str | None = None) -> dict:
        """Return a deterministic placeholder image using picsum.photos."""
        # Use a hash of the prompt to always return the same image for the same prompt
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        url = f"https://picsum.photos/seed/{seed}/1024/1024"
        result: dict = {"prompt": prompt, "url": url, "mime_type": "image/jpeg", "source": "placeholder"}
        if error:
            result["error"] = error
            result["note"] = "DALL-E failed; showing placeholder. Set OPENAI_API_KEY for real generation."
        else:
            result["note"] = "Set OPENAI_API_KEY to enable real DALL-E image generation."
        return result
