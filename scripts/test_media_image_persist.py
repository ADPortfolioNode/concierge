#!/usr/bin/env python3
"""Regression tests for image byte validation and format sniffing."""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_rejects_tiny_embedded_placeholder() -> None:
    import base64

    from core.media_persist import is_valid_image_bytes, save_image_bytes

    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    assert not is_valid_image_bytes(tiny_png)
    fname, path = save_image_bytes(tiny_png, prompt="tiny", source="test")
    assert fname == "" and path == ""


def test_sniff_png_extension() -> None:
    from PIL import Image

    from core.media_persist import save_image_bytes, sniff_image_format

    buf = BytesIO()
    Image.new("RGB", (64, 64), color=(10, 20, 30)).save(buf, format="PNG")
    content = buf.getvalue()
    assert sniff_image_format(content) == ("image/png", "png")
    fname, path = save_image_bytes(content, prompt="png-test", source="test")
    assert fname.endswith(".png"), fname
    assert path.endswith(".png"), path


def test_yin_yang_placeholder_renders() -> None:
    from core.media_persist import is_valid_image_bytes
    from core.placeholder_image import render_yin_yang_placeholder
    from plugins.image_generation_plugin import ImageGenerationPlugin

    raw = render_yin_yang_placeholder("concierge logo", seed=42)
    assert is_valid_image_bytes(raw)
    assert len(raw) > 5000

    out = ImageGenerationPlugin._placeholder("test logo for concierge", error="simulated failure")
    url = out.get("url", "")
    assert url.startswith("/media/images/"), out
    assert out.get("source") == "placeholder-yin-yang", out
    media_dir = Path(__file__).resolve().parents[1] / "media" / "images"
    fname = url.rsplit("/", 1)[-1]
    saved = media_dir / fname
    assert saved.exists(), f"missing {saved}"
    assert saved.stat().st_size >= 5000, saved.stat().st_size


def main() -> int:
    test_rejects_tiny_embedded_placeholder()
    test_sniff_png_extension()
    test_yin_yang_placeholder_renders()
    print("OK: media image persist tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())