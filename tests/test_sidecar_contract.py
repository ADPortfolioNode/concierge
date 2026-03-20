import json
from pathlib import Path

from plugins.image_generation_plugin import ImageGenerationPlugin


def test_sidecar_contains_expected_fields():
    # create a tiny PNG and save via plugin helper
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    import base64

    content = base64.b64decode(tiny_png_b64)
    fname = ImageGenerationPlugin._save_bytes_to_media_static(
        content, "contract-prompt", metadata={"prompt": "contract-prompt", "source": "test", "mime_type": "image/png"}
    )

    root = Path(__file__).resolve().parent.parent
    meta_path = root / "media" / "images" / (fname + ".json")
    assert meta_path.exists(), "sidecar metadata must exist"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # required fields
    for k in ("filename", "prompt", "mime_type", "created_at", "size"):
        assert k in meta, f"sidecar missing {k}"

    assert meta["filename"] == fname
    assert isinstance(meta["size"], int)