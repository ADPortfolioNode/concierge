import os
import json
import base64
from pathlib import Path
from fastapi.testclient import TestClient

from app import app


def _ensure_sample_image():
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQImWNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    content = base64.b64decode(tiny_png_b64)
    media_dir = Path(__file__).resolve().parent.parent / "media" / "images"
    media_dir.mkdir(parents=True, exist_ok=True)
    fname = f"test_img_{int(Path(__file__).stat().st_mtime)}.png"
    img_path = media_dir / fname
    img_path.write_bytes(content)
    sidecar = {
        "filename": fname,
        "mime_type": "image/png",
        "created_at": "2026-01-01T00:00:00Z",
        "size": len(content),
        "source": "test",
        "remote_url": f"/media/images/{fname}",
    }
    (media_dir / (fname + ".json")).write_text(json.dumps(sidecar))
    return fname


def test_media_list_and_timeline_graph():
    fname = _ensure_sample_image()
    # enable absolute URLs feature flag
    os.environ['FEATURE_FLAGS'] = 'media_absolute_urls'
    with TestClient(app) as client:
        r = client.get("/api/v1/concierge/media")
        assert r.status_code == 200
        payload = r.json()
        assert payload.get("status") == "success"
        data = payload.get("data")
        assert isinstance(data, list)

        filenames = [item.get("metadata", {}).get("filename") or item.get("filename") for item in data]
        assert fname in filenames

        r2 = client.get("/api/v1/concierge/timeline/graph")
        assert r2.status_code == 200
        ctype = r2.headers.get("content-type", "")
        assert "image" in ctype
