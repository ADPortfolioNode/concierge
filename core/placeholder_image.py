"""Yin-yang themed placeholder images for offline / fallback image generation."""
from __future__ import annotations

import hashlib
from io import BytesIO


def _palette(seed: int) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """Deterministic yin-yang palette from *seed*."""
    dark = (14 + seed % 18, 14 + (seed * 3) % 18, 24 + (seed * 5) % 20)
    light = (245 - seed % 10, 245 - (seed * 2) % 10, 250)
    ring = (90 + seed % 40, 75 + (seed * 2) % 35, 45 + seed % 30)
    return dark, light, ring


def render_yin_yang_placeholder(
    prompt: str = "",
    *,
    size: int = 1024,
    seed: int | None = None,
) -> bytes:
    """Render a yin-yang symbol with optional caption; returns JPEG bytes."""
    from PIL import Image, ImageDraw, ImageFont

    if seed is None:
        seed = int(hashlib.md5((prompt or "concierge").encode()).hexdigest()[:8], 16) % 1000

    dark, light, ring = _palette(seed)
    img = Image.new("RGB", (size, size), light)
    draw = ImageDraw.Draw(img)

    caption_h = 120 if prompt else 0
    cx, cy = size // 2, (size - caption_h) // 2
    r = int(min(size, size - caption_h) * 0.34)

    # Decorative outer ring
    draw.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=ring)
    bbox = [cx - r, cy - r, cx + r, cy + r]

    # Yin-yang body
    draw.ellipse(bbox, fill=light, outline=dark, width=4)
    draw.pieslice(bbox, 90, 270, fill=dark)

    hr = r // 2
    draw.ellipse([cx - hr, cy - r - hr, cx + hr, cy - r + hr], fill=light)
    draw.ellipse([cx - hr, cy + r - hr, cx + hr, cy + r + hr], fill=dark)

    dot_r = max(6, r // 6)
    draw.ellipse([cx - dot_r, cy - r - dot_r, cx + dot_r, cy - r + dot_r], fill=dark)
    draw.ellipse([cx - dot_r, cy + r - dot_r, cx + dot_r, cy + r + dot_r], fill=light)

    if prompt:
        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except OSError:
            font = ImageFont.load_default()
        label = (prompt[:96] + "…") if len(prompt) > 96 else prompt
        tb = draw.textbbox((0, 0), label, font=font)
        tw = tb[2] - tb[0]
        draw.text(
            ((size - tw) / 2, size - caption_h + 28),
            label,
            fill=dark,
            font=font,
        )
        draw.text(
            ((size - tw) / 2, size - caption_h + 62),
            "Yin-yang placeholder — set OPENAI_API_KEY for real images",
            fill=ring,
            font=font,
        )

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()