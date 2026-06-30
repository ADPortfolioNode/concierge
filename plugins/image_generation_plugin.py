"""Image-generation plugin.

Provider chain (first success wins):

1. OpenAI ``gpt-image-1`` when ``OPENAI_API_KEY`` is set
2. Gemini native image models when OpenAI fails or is unavailable
3. Local Ollama / Llama image models (``/v1/images/generations``)
4. Persisted placeholder image
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx

from config.settings import get_settings
from plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


def _get_media_images_dir() -> Path:
    settings = get_settings()
    media_dir = settings.media_images_dir
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def _parse_prompt(input_data) -> str:
    if isinstance(input_data, dict):
        prompt = str(
            input_data.get("prompt")
            or input_data.get("input")
            or input_data.get("text")
            or ""
        ).strip()
    else:
        prompt = str(input_data).strip()
    return prompt or "abstract colorful art"


def _ollama_configured() -> bool:
    base = (get_settings().ollama_base_url or "").strip().lower()
    return bool(base) and base not in ("none", "disabled", "false", "0")


class ImageGenerationPlugin(BasePlugin):
    name = "image_generation"
    description = (
        "Generates images via OpenAI, Gemini, or local Ollama/Llama models, "
        "then placeholder fallback."
    )
    version = "0.4.0"

    async def run(self, input_data: str) -> dict:
        prompt = _parse_prompt(input_data)
        settings = get_settings()

        if settings.openai_api_key:
            return await self._dalle(prompt, settings.openai_api_key)

        errors: list[str] = []
        if settings.gemini_api_key:
            try:
                return await self._gemini_image(prompt, settings.gemini_api_key)
            except Exception as exc:
                logger.exception("Gemini image generation failed: %s", exc)
                errors.append(str(exc))

        ollama_result = await self._try_ollama_fallback(prompt, "; ".join(errors))
        if ollama_result:
            return ollama_result

        return self._placeholder(prompt, error="; ".join(errors) if errors else None)

    async def _try_gemini_fallback(self, prompt: str, openai_error: str) -> dict | None:
        settings = get_settings()
        if not settings.gemini_api_key:
            return None
        try:
            logger.info("OpenAI image failed (%s); attempting Gemini fallback", openai_error[:120])
            return await self._gemini_image(prompt, settings.gemini_api_key)
        except Exception as gexc:
            logger.exception("Gemini image fallback failed: %s", gexc)
            return None

    async def _try_ollama_fallback(self, prompt: str, prior_error: str) -> dict | None:
        if not _ollama_configured():
            return None
        try:
            logger.info(
                "Attempting Ollama/Llama image fallback after prior failure: %s",
                (prior_error or "no cloud providers")[:120],
            )
            return await self._ollama_image(prompt)
        except Exception as oexc:
            logger.exception("Ollama image fallback failed: %s", oexc)
            return None

    async def _dalle(self, prompt: str, api_key: str) -> dict:
        """Call OpenAI Images API (gpt-image-1)."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
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
                if resp.status_code != 200:
                    logger.error("OpenAI image request failed %s %s", resp.status_code, resp.text)
                resp.raise_for_status()
                data = resp.json()
            item = data["data"][0]
            if "url" in item:
                remote = item["url"]
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        dl = await client.get(remote)
                        dl.raise_for_status()
                        content = dl.content
                    mime = dl.headers.get("content-type", "image/jpeg")
                except Exception:
                    content = b""
                    mime = "image/jpeg"
            else:
                blob = item.get("b64_json")
                content = base64.b64decode(blob) if blob else b""
                mime = "image/jpeg"

            revised = item.get("revised_prompt", prompt)
            metadata = {
                "prompt": prompt,
                "revised_prompt": revised,
                "source": "gpt-image-1",
                "remote_url": item.get("url") if "url" in item else None,
                "mime_type": mime,
            }
            filename = self._save_bytes_to_media(content, prompt, metadata=metadata)
            return {
                "prompt": prompt,
                "revised_prompt": revised,
                "url": f"/media/images/{filename}",
                "mime_type": mime,
                "source": "gpt-image-1",
            }
        except Exception as exc:
            logger.exception("OpenAI image generation failed: %s", exc)
            gemini_result = await self._try_gemini_fallback(prompt, str(exc))
            if gemini_result:
                gemini_result["openai_error"] = str(exc)
                return gemini_result
            ollama_result = await self._try_ollama_fallback(prompt, str(exc))
            if ollama_result:
                ollama_result["openai_error"] = str(exc)
                return ollama_result
            return self._placeholder(prompt, error=str(exc))

    def _package_image_result(
        self,
        prompt: str,
        content: bytes,
        mime: str,
        source: str,
        *,
        revised_prompt: str | None = None,
    ) -> dict:
        revised = revised_prompt or prompt
        metadata = {
            "prompt": prompt,
            "revised_prompt": revised,
            "source": source,
            "mime_type": mime,
        }
        filename = self._save_bytes_to_media(content, prompt, metadata=metadata)
        return {
            "prompt": prompt,
            "revised_prompt": revised,
            "url": f"/media/images/{filename}",
            "mime_type": mime,
            "source": source,
        }

    async def _decode_openai_style_item(self, item: dict) -> Tuple[bytes, str]:
        if "url" in item:
            remote = item["url"]
            async with httpx.AsyncClient(timeout=60) as client:
                dl = await client.get(remote)
                dl.raise_for_status()
                content = dl.content
            mime = dl.headers.get("content-type", "image/png")
            return content, mime
        blob = item.get("b64_json")
        if blob:
            return base64.b64decode(blob), "image/png"
        return b"", ""

    async def _ollama_image(self, prompt: str) -> dict:
        """Generate an image via local Ollama's OpenAI-compatible images API."""
        settings = get_settings()
        base = settings.ollama_base_url.rstrip("/")
        raw_models = settings.ollama_image_models or "x/flux2-klein,x/z-image-turbo"
        models = [m.strip() for m in raw_models.split(",") if m.strip()]
        last_exc: Exception | None = None

        for model in models:
            url = f"{base}/v1/images/generations"
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
            }
            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        logger.error(
                            "Ollama image %s failed %s %s",
                            model,
                            resp.status_code,
                            resp.text[:500],
                        )
                    resp.raise_for_status()
                    data = resp.json()

                items = data.get("data") or []
                if not items:
                    raise RuntimeError(f"Ollama model {model} returned no image data")

                content, mime = await self._decode_openai_style_item(items[0])
                if not content:
                    raise RuntimeError(f"Ollama model {model} returned empty image bytes")

                revised = items[0].get("revised_prompt", prompt)
                return self._package_image_result(
                    prompt,
                    content,
                    mime,
                    f"ollama:{model}",
                    revised_prompt=revised,
                )
            except Exception as exc:
                logger.warning("Ollama image model %s failed: %s", model, exc)
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError("Ollama image generation failed: no models configured")

    @staticmethod
    def _extract_gemini_image_bytes(data: dict) -> Tuple[bytes, str]:
        """Parse inline image bytes from a Gemini generateContent response."""
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data") or {}
                b64 = inline.get("data")
                if b64:
                    mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    return base64.b64decode(b64), mime
        return b"", ""

    async def _gemini_image(self, prompt: str, api_key: str) -> dict:
        """Generate an image via Gemini native image models (generateContent API)."""
        settings = get_settings()
        raw_models = settings.gemini_image_models or "gemini-2.5-flash-image,gemini-3.1-flash-image"
        models = [m.strip() for m in raw_models.split(",") if m.strip()]
        last_exc: Exception | None = None

        for model in models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            }
            headers = {"Content-Type": "application/json"}
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code != 200:
                        logger.error("Gemini image %s failed %s %s", model, resp.status_code, resp.text[:500])
                    resp.raise_for_status()
                    data = resp.json()

                content, mime = self._extract_gemini_image_bytes(data)
                if not content:
                    raise RuntimeError(f"Gemini model {model} returned no image data")

                return self._package_image_result(
                    prompt,
                    content,
                    mime,
                    f"gemini:{model}",
                )
            except Exception as exc:
                logger.warning("Gemini image model %s failed: %s", model, exc)
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError("Gemini image generation failed: no models configured")

    @staticmethod
    def _placeholder(prompt: str, error: str | None = None) -> dict:
        """Return a deterministic placeholder image using picsum.photos."""
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        remote = f"https://picsum.photos/seed/{seed}/1024/1024"
        try:
            resp = httpx.get(remote, timeout=20)
            resp.raise_for_status()
            content = resp.content
            img_path = ImageGenerationPlugin._save_bytes_to_media_static(
                content,
                prompt,
                metadata={
                    "prompt": prompt,
                    "source": "placeholder",
                    "remote_url": remote,
                    "mime_type": resp.headers.get("content-type", "image/jpeg"),
                },
            )
            url = f"/media/images/{img_path}"
            mime = resp.headers.get("content-type", "image/jpeg")
            source = "placeholder"
        except Exception:
            try:
                from io import BytesIO

                from PIL import Image, ImageDraw, ImageFont

                bg = (int(seed * 137) % 256, int(seed * 61) % 256, int(seed * 199) % 256)
                img = Image.new("RGB", (1024, 1024), color=bg)
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("arial.ttf", 28)
                except Exception:
                    font = ImageFont.load_default()
                text = (prompt[:120] + "...") if len(prompt) > 120 else prompt
                w, h = draw.textsize(text, font=font)
                draw.text(((1024 - w) / 2, (1024 - h) / 2), text, fill=(255, 255, 255), font=font)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=90)
                content = buf.getvalue()
                fname = ImageGenerationPlugin._save_bytes_to_media_static(
                    content,
                    prompt,
                    metadata={"prompt": prompt, "source": "placeholder-local", "mime_type": "image/jpeg"},
                )
                url = f"/media/images/{fname}"
                mime = "image/jpeg"
                source = "placeholder-local"
            except Exception:
                try:
                    tiny_png_b64 = (
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
                        "ASsJTYQAAAAASUVORK5CYII="
                    )
                    content = base64.b64decode(tiny_png_b64)
                    fname = ImageGenerationPlugin._save_bytes_to_media_static(
                        content,
                        prompt,
                        metadata={"prompt": prompt, "source": "placeholder-embedded", "mime_type": "image/png"},
                    )
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
            result["note"] = (
                f"Image generation failed ({error}). "
                "OpenAI, Gemini, and Ollama/Llama fallbacks were attempted where configured. "
                "Showing a placeholder image instead."
            )
        else:
            result["note"] = (
                "Set OPENAI_API_KEY, GEMINI_API_KEY, or OLLAMA_BASE_URL for real image generation."
            )
        return result

    def _save_bytes_to_media(self, content: bytes, prompt: str, metadata: Optional[dict] = None) -> str:
        return ImageGenerationPlugin._save_bytes_to_media_static(content, prompt, metadata)

    @staticmethod
    def _save_bytes_to_media_static(content: bytes, prompt: str, metadata: Optional[dict] = None) -> str:
        try:
            media_dir = _get_media_images_dir()
            h = hashlib.md5(prompt.encode()).hexdigest()[:10]
            ext = "png" if (metadata or {}).get("mime_type", "").endswith("png") else "jpg"
            fname = f"img_{h}_{int(time.time())}.{ext}"
            dest = media_dir / fname
            dest.write_bytes(content)
            try:
                dest.chmod(0o644)
            except Exception:
                pass
            try:
                meta = metadata or {}
                meta.setdefault("filename", fname)
                meta.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                try:
                    meta.setdefault("size", dest.stat().st_size)
                except Exception:
                    meta.setdefault("size", len(content))
                meta_path = media_dir / (fname + ".json")
                meta_path.write_text(json.dumps(meta, ensure_ascii=False))
            except Exception:
                logger.exception("Failed to write sidecar metadata for %s", fname)
            try:
                from core.observability import MEDIA_SAVED

                MEDIA_SAVED.inc()
            except Exception:
                pass
            return fname
        except Exception:
            return ""