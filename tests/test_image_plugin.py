import json
from pathlib import Path

from plugins.image_generation_plugin import ImageGenerationPlugin


def test_save_bytes_to_media_static_creates_files(tmp_path):
    # create a tiny PNG payload (1x1 transparent)
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    import base64

    content = base64.b64decode(tiny_png_b64)

    # call the static helper (it writes into repo media/images by design)
    fname = ImageGenerationPlugin._save_bytes_to_media_static(content, "unittest-prompt", metadata={
        "prompt": "unittest-prompt",
        "source": "test",
        "mime_type": "image/png",
    })

    assert fname, "filename should be returned"

    root = Path(__file__).resolve().parent.parent
    img_path = root / "media" / "images" / fname
    meta_path = root / "media" / "images" / (fname + ".json")

    assert img_path.exists(), f"image file {img_path} should exist"
    assert meta_path.exists(), f"sidecar {meta_path} should exist"

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta.get("filename") == fname
    assert meta.get("prompt") == "unittest-prompt"
    assert meta.get("mime_type") == "image/png"
    assert meta.get("size") == img_path.stat().st_size
