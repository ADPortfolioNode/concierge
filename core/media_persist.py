"""Download remote images and persist under media/images with stable local paths."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Real image URLs with extensions — exclude stock placeholder hosts.
_PLACEHOLDER_HOSTS = re.compile(
    r"picsum\.photos|images\.unsplash\.com|placehold\.co|placeholder\.com|via\.placeholder|loremflickr\.com",
    re.IGNORECASE,
)
_IMAGE_URL_RE = re.compile(
    r"(https?://[^\s\)'\"<>]+\.(?:png|jpe?g|gif|webp|svg|avif)(?:\?\S*)?)",
    re.IGNORECASE,
)


def _is_placeholder_url(url: str) -> bool:
    return bool(_PLACEHOLDER_HOSTS.search(url))


def media_images_dir() -> Path:
    path = get_settings().media_images_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


MIN_IMAGE_BYTES = 100


def sniff_image_format(content: bytes) -> tuple[str, str] | None:
    """Return ``(mime_type, extension)`` from magic bytes, or *None* if unrecognized."""
    if not content or len(content) < 12:
        return None
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def is_valid_image_bytes(content: bytes, *, min_size: int = MIN_IMAGE_BYTES) -> bool:
    """Reject empty, truncated, or placeholder-sized payloads."""
    return bool(content) and len(content) >= min_size and sniff_image_format(content) is not None


def media_type_for_path(path: Path) -> str:
    """Sniff Content-Type from file bytes; fall back to extension guess."""
    try:
        sniffed = sniff_image_format(path.read_bytes()[:16])
        if sniffed:
            return sniffed[0]
    except OSError:
        pass
    ext = path.suffix.lower().lstrip(".")
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")


def _ext_from_mime(mime: str) -> str:
    m = (mime or "").lower()
    if "png" in m:
        return "png"
    if "gif" in m:
        return "gif"
    if "webp" in m:
        return "webp"
    if "svg" in m:
        return "svg"
    return "jpg"


def save_image_bytes(
    content: bytes,
    *,
    prompt: str | None = None,
    source: str = "saved",
    mime_type: str = "image/jpeg",
    remote_url: str | None = None,
) -> tuple[str, str]:
    """Write image bytes to disk. Returns ``(filename, local_path)`` where local_path is ``/media/images/...``."""
    if not is_valid_image_bytes(content):
        return "", ""
    sniffed = sniff_image_format(content)
    if sniffed:
        mime_type, ext = sniffed
    else:
        ext = _ext_from_mime(mime_type)
    media_dir = media_images_dir()
    seed = hashlib.md5((prompt or remote_url or str(len(content))).encode()).hexdigest()[:10]
    fname = f"img_{seed}_{int(time.time())}.{ext}"
    dest = media_dir / fname
    dest.write_bytes(content)
    try:
        dest.chmod(0o644)
    except OSError:
        pass
    meta: dict[str, Any] = {
        "filename": fname,
        "prompt": prompt,
        "source": source,
        "mime_type": mime_type,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "size": len(content),
    }
    if remote_url:
        meta["remote_url"] = remote_url
    try:
        (media_dir / f"{fname}.json").write_text(json.dumps(meta, ensure_ascii=False))
    except OSError:
        logger.exception("Failed writing sidecar for %s", fname)
    try:
        from core.observability import MEDIA_SAVED

        MEDIA_SAVED.inc()
    except Exception:
        pass
    return fname, f"/media/images/{fname}"


def persist_remote_url(url: str, *, prompt: str | None = None, timeout: float = 30.0) -> str | None:
    """Fetch a remote image URL and return a local ``/media/images/...`` path."""
    if not url or not isinstance(url, str):
        return None
    if _is_placeholder_url(url):
        return None
    if url.startswith("/media/images/"):
        return url
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if not ctype.startswith("image") and "octet-stream" not in ctype:
                return None
            _, local = save_image_bytes(
                resp.content,
                prompt=prompt,
                source="remote-mirror",
                mime_type=ctype or "image/jpeg",
                remote_url=url,
            )
            return local or None
    except Exception:
        logger.exception("Failed to persist remote image %s", url)
        return None


def rewrite_image_urls(text: str, *, prompt: str | None = None) -> str:
    """Replace remote image URLs in *text* with persisted ``/media/images/...`` paths."""
    if not text or not isinstance(text, str):
        return text
    out = text
    seen: set[str] = set()
    for match in _IMAGE_URL_RE.finditer(text):
        url = match.group(1).rstrip(".,;)")
        if url in seen or url.startswith("/media/images/") or _is_placeholder_url(url):
            continue
        seen.add(url)
        local = persist_remote_url(url, prompt=prompt)
        if local:
            out = out.replace(url, local)
    return out


async def rewrite_image_urls_async(text: str, *, prompt: str | None = None) -> str:
    if not text or not isinstance(text, str):
        return text
    out = text
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for match in _IMAGE_URL_RE.finditer(text):
            url = match.group(1).rstrip(".,;)")
            if url in seen or url.startswith("/media/images/") or _is_placeholder_url(url):
                continue
            seen.add(url)
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                ctype = resp.headers.get("content-type", "")
                if not ctype.startswith("image") and "octet-stream" not in ctype:
                    continue
                _, local = save_image_bytes(
                    resp.content,
                    prompt=prompt,
                    source="remote-mirror",
                    mime_type=ctype or "image/jpeg",
                    remote_url=url,
                )
                if local:
                    out = out.replace(url, local)
            except Exception:
                logger.exception("Failed to persist remote image %s", url)
    return out