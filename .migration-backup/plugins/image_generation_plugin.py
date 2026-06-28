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
import base64
import json
import time
from pathlib import Path
from typing import Optional
import httpx
from config.settings import get_settings

from plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


def _get_media_images_dir() -> Path:
    settings = get_settings()
    media_dir = settings.media_images_dir
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


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

            # save bytes to media/images and return local URL + sidecar metadata
            revised = item.get("revised_prompt", prompt)
            metadata = {
                "prompt": prompt,
                "revised_prompt": revised,
                "source": "gpt-image-1",
                "remote_url": item.get("url") if "url" in item else None,
                "mime_type": mime,
            }
            filename = self._save_bytes_to_media(content, prompt, metadata=metadata)
            return {"prompt": prompt, "revised_prompt": revised, "url": f"/media/images/{filename}", "mime_type": mime, "source": "gpt-image-1"}
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
        revised = item.get("revised_prompt", prompt)
        metadata = {
            "prompt": prompt,
            "revised_prompt": revised,
            "source": "gemini",
            "remote_url": item.get("url") if "url" in item else None,
            "mime_type": mime,
        }
        filename = self._save_bytes_to_media(content, prompt, metadata=metadata)
        # mark the source so callers know which provider produced it
        return {"prompt": prompt, "revised_prompt": revised, "url": f"/media/images/{filename}", "mime_type": mime, "source": "gemini"}

    @staticmethod
    def _placeholder(prompt: str, error: str | None = None) -> dict:
        """Return a deterministic placeholder image using picsum.photos."""
        # Use a hash of the prompt to always return the same image for the same prompt
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        remote = f"https://picsum.photos/seed/{seed}/1024/1024"
        # attempt to download the placeholder and persist locally
        try:
            resp = httpx.get(remote, timeout=20)
            resp.raise_for_status()
            content = resp.content
            # save to media
            img_path = ImageGenerationPlugin._save_bytes_to_media_static(content, prompt, metadata={
                "prompt": prompt,
                "source": "placeholder",
                "remote_url": remote,
                "mime_type": resp.headers.get("content-type", "image/jpeg"),
            })
            url = f"/media/images/{img_path}"
            mime = resp.headers.get("content-type", "image/jpeg")
            source = "placeholder"
        except Exception:
            # fallback: create a simple local PNG placeholder if network
            # download fails or httpx is unavailable. This guarantees we
            # always return a local `/media/images/...` URL.
            try:
                from PIL import Image, ImageDraw, ImageFont
                from io import BytesIO

                # create a simple square image with a background color
                bg = (int(seed * 137) % 256, int(seed * 61) % 256, int(seed * 199) % 256)
                img = Image.new('RGB', (1024, 1024), color=bg)
                draw = ImageDraw.Draw(img)
                # draw the prompt text in the center (fallback font)
                try:
                    font = ImageFont.truetype('arial.ttf', 28)
                except Exception:
                    font = ImageFont.load_default()
                text = (prompt[:120] + '...') if len(prompt) > 120 else prompt
                w, h = draw.textsize(text, font=font)
                draw.text(((1024 - w) / 2, (1024 - h) / 2), text, fill=(255, 255, 255), font=font)
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=90)
                content = buf.getvalue()
                fname = ImageGenerationPlugin._save_bytes_to_media_static(content, prompt, metadata={
                    "prompt": prompt,
                    "source": "placeholder-local",
                    "mime_type": "image/jpeg",
                })
                url = f"/media/images/{fname}"
                mime = "image/jpeg"
                source = "placeholder-local"
            except Exception:
                # last-resort fallback: write a tiny embedded PNG to disk
                try:
                    tiny_png_b64 = (
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
                        "ASsJTYQAAAAASUVORK5CYII="
                    )
                    content = base64.b64decode(tiny_png_b64)
                    fname = ImageGenerationPlugin._save_bytes_to_media_static(content, prompt, metadata={
                        "prompt": prompt,
                        "source": "placeholder-embedded",
                        "mime_type": "image/png",
                    })
                    if fname:
                        url = f"/media/images/{fname}"
                        mime = "image/png"
                        source = "placeholder-embedded"
                    else:
                        url = remote
                        mime = "image/jpeg"
                        source = "placeholder-remote"
                except Exception:
                    url = remote
                    mime = "image/jpeg"
                    source = "placeholder-remote"

        result: dict = {"prompt": prompt, "url": url, "mime_type": mime, "source": source}
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

    # ----------------- helpers -------------------------------------------
    def _save_bytes_to_media(self, content: bytes, prompt: str, metadata: Optional[dict] = None) -> str:
        """Save bytes into project media/images and return filename. Also writes a .json sidecar."""
        try:
            media_dir = _get_media_images_dir()
            # create filename from prompt hash + short ts
            h = hashlib.md5(prompt.encode()).hexdigest()[:10]
            fname = f"img_{h}_{int(__import__('time').time())}.jpg"
            dest = media_dir / fname
            dest.write_bytes(content)
            try:
                dest.chmod(0o644)
            except Exception:
                pass
            # write sidecar metadata file (JSON) next to the image
            try:
                meta = metadata or {}
                meta.setdefault("filename", fname)
                meta.setdefault("created_at", time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
                try:
                    meta.setdefault("size", dest.stat().st_size)
                except Exception:
                    meta.setdefault("size", len(content))
                meta_path = media_dir / (fname + ".json")
                meta_path.write_text(json.dumps(meta, ensure_ascii=False))
                try:
                    meta_path.chmod(0o644)
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to write sidecar metadata for %s", fname)
            try:
                # increment media saved metric if available
                from core.observability import MEDIA_SAVED
                try:
                    MEDIA_SAVED.inc()
                except Exception:
                    pass
            except Exception:
                pass
            return fname
        except Exception:
            # as a best-effort fallback return an empty name
            return ""

    @staticmethod
    def _save_bytes_to_media_static(content: bytes, prompt: str, metadata: Optional[dict] = None) -> str:
        """Static helper usable from staticmethods to persist bytes. Also writes a .json sidecar."""
        try:
            media_dir = _get_media_images_dir()
            h = hashlib.md5(prompt.encode()).hexdigest()[:10]
            fname = f"img_{h}_{int(__import__('time').time())}.jpg"
            dest = media_dir / fname
            dest.write_bytes(content)
            try:
                dest.chmod(0o644)
            except Exception:
                pass
            # write sidecar metadata
            try:
                meta = metadata or {}
                meta.setdefault("filename", fname)
                meta.setdefault("created_at", time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
                try:
                    meta.setdefault("size", dest.stat().st_size)
                except Exception:
                    meta.setdefault("size", len(content))
                meta_path = media_dir / (fname + ".json")
                meta_path.write_text(json.dumps(meta, ensure_ascii=False))
                try:
                    meta_path.chmod(0o644)
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to write static sidecar metadata for %s", fname)
            return fname
        except Exception:
            return ""
