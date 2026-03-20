import json
from pathlib import Path

from fastapi.testclient import TestClient
import os

from plugins.image_generation_plugin import ImageGenerationPlugin
import matplotlib
matplotlib.use('Agg')


def test_media_endpoint_and_timeline_graph():
    # ensure a sample image + sidecar exist
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    import base64

    content = base64.b64decode(tiny_png_b64)
    fname = ImageGenerationPlugin._save_bytes_to_media_static(
        content,
        "integration-prompt",
        metadata={"prompt": "integration-prompt", "source": "test", "mime_type": "image/png"},
    )

    root = Path(__file__).resolve().parent.parent
    img_path = root / "media" / "images" / fname
    meta_path = root / "media" / "images" / (fname + ".json")

    assert img_path.exists()
    assert meta_path.exists()

    # import the app and run TestClient
    from app import app

    # enable server-side absolute media URLs for this request
    os.environ['FEATURE_FLAGS'] = 'media_absolute_urls'
    with TestClient(app) as client:
        # media listing
        r = client.get("/api/v1/concierge/media")
        assert r.status_code == 200
        payload = r.json()
        # accept either a bare list or an envelope {"data": [...]}
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
        else:
            data = payload
        assert isinstance(data, list)

        # ensure our file is listed (by filename)
        filenames = [item.get("metadata", {}).get("filename") or item.get("filename") for item in data]
        assert fname in filenames

        # timeline graph should return an image (PNG) even if empty
        r2 = client.get("/api/v1/concierge/timeline/graph")
        assert r2.status_code == 200
        ctype = r2.headers.get("content-type", "")
        assert "image" in ctype

        # verify server returned absolute URL when feature flag enabled
        found = False
        for item in data:
            url = item.get('url')
            if url and url.startswith('http'):
                found = True
                break
        assert found, "expected at least one absolute media URL when flag enabled"
