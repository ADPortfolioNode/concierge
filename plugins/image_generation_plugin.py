"""Image-generation plugin.

When ``OPENAI_API_KEY`` is set, generates real images via OpenAI's image API (`gpt-image-1` model).
Otherwise returns a local yin-yang themed placeholder so the pipeline stays end-to-end functional.
"""

from __future__ import annotations

import hashlib
import logging

import httpx
from config.settings import get_settings

from core.media_persist import is_valid_image_bytes, save_image_bytes
from core.placeholder_image import render_yin_yang_placeholder
from plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class ImageGenerationPlugin(BasePlugin):
    name = "image_generation"
    description = "Generates images from text prompts via DALL-E (requires OPENAI_API_KEY)."
    version = "0.2.0"

    async def run(self, input_data: str) -> dict:
        if isinstance(input_data, dict):
            prompt = str(
                input_data.get("prompt")
                or input_data.get("input")
                or input_data.get("text")
                or ""
            ).strip()
        else:
            prompt = str(input_data).strip()
        if not prompt:
            prompt = "abstract colorful art"

        settings = get_settings()
        api_key = settings.openai_api_key
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
            # versions returned a direct ``url``.  Persist the image locally
            # under the project's media directory so the frontend can load it
            # from a stable endpoint.
            if "url" in item:
                remote = item["url"]
                # download the remote URL and save locally
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(remote)
                        resp.raise_for_status()
                        content = resp.content
                except Exception:
                    content = b""
                mime = resp.headers.get("content-type", "image/jpeg") if 'resp' in locals() else "image/jpeg"
            else:
                blob = item.get("b64_json")
                content = base64.b64decode(blob) if blob else b""
                mime = "image/jpeg"

            if not is_valid_image_bytes(content):
                return self._placeholder(prompt, error="empty or invalid image data from OpenAI")

            revised = item.get("revised_prompt", prompt)
            filename, local_path = save_image_bytes(
                content,
                prompt=prompt,
                source="gpt-image-1",
                mime_type=mime,
                remote_url=item.get("url") if "url" in item else None,
            )
            if not filename:
                return self._placeholder(prompt, error="failed to persist OpenAI image")
            return {
                "prompt": prompt,
                "revised_prompt": revised,
                "url": local_path,
                "mime_type": mime,
                "source": "gpt-image-1",
            }
        except Exception as exc:
            # exc may be an HTTPStatusError; include any response text if
            # available to help troubleshooting.
            logger.exception("DALL-E generation failed: %s", exc)
            # if the error appears to be due to billing or rate limits, and we
            # have a Gemini key, try that before giving up entirely
            msg = str(exc).lower()
            settings = get_settings()
            gemini_key = settings.gemini_api_key
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
            remote = item["url"]
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(remote)
                    resp.raise_for_status()
                    content = resp.content
            except Exception:
                content = b""
            mime = resp.headers.get("content-type", "image/jpeg") if 'resp' in locals() else "image/jpeg"
        else:
            blob = item.get("b64_json")
            content = base64.b64decode(blob) if blob else b""
            mime = "image/jpeg"
        if not is_valid_image_bytes(content):
            return self._placeholder(prompt, error="empty or invalid image data from Gemini")

        revised = item.get("revised_prompt", prompt)
        filename, local_path = save_image_bytes(
            content,
            prompt=prompt,
            source="gemini",
            mime_type=mime,
            remote_url=item.get("url") if "url" in item else None,
        )
        if not filename:
            return self._placeholder(prompt, error="failed to persist Gemini image")
        return {"prompt": prompt, "revised_prompt": revised, "url": local_path, "mime_type": mime, "source": "gemini"}

    @staticmethod
    def _placeholder(prompt: str, error: str | None = None) -> dict:
        """Return a deterministic yin-yang themed placeholder saved under /media/images/."""
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        mime = "image/jpeg"
        source = "placeholder-yin-yang"
        try:
            content = render_yin_yang_placeholder(prompt, seed=seed)
            if not is_valid_image_bytes(content):
                raise ValueError("yin-yang placeholder render invalid")
            _, url = save_image_bytes(
                content,
                prompt=prompt,
                source=source,
                mime_type=mime,
            )
            if not url:
                raise ValueError("failed to persist yin-yang placeholder")
        except Exception:
            logger.exception("Yin-yang placeholder render failed for prompt %r", prompt[:80])
            return {
                "prompt": prompt,
                "url": "",
                "mime_type": mime,
                "source": "placeholder-failed",
                "status": "failed",
                "error": error or "placeholder render failed",
                "note": "Image generation unavailable and yin-yang placeholder could not be saved.",
            }

        result: dict = {"prompt": prompt, "url": url, "mime_type": mime, "source": source}
        if error:
            result["error"] = error
            result["note"] = (
                f"Image generation failed ({error}). "
                "Showing a yin-yang placeholder instead. "
                "Check OPENAI_API_KEY, billing, or rate limits."
            )
        else:
            result["note"] = "Set OPENAI_API_KEY to enable real image generation via OpenAI."
        return result


