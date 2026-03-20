import os
import time
import requests
from pathlib import Path


def test_post_message_persists_remote_image():
    url = 'http://localhost:8001/api/v1/concierge/message'
    # Use an existing local media file as the "remote" resource to avoid
    # external network dependence in CI. Pick the newest file under media/images
    root = Path(__file__).resolve().parent.parent
    media_dir = root / 'media' / 'images'
    # Accept common image suffixes so tests stay stable if default format changes
    exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
    imgs = sorted([p for p in media_dir.iterdir() if p.suffix.lower() in exts], key=lambda p: p.stat().st_mtime, reverse=True)
    assert imgs, 'no sample media images available to test with'
    sample = imgs[0].name
    remote_url = f'http://localhost:8001/media/images/{sample}'
    payload = {"message": f"Please fetch this image: {remote_url}"}
    r = requests.post(url, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json().get('data')
    assert data, 'response missing data'
    content = data.get('content', '')
    assert '/media/images/' in content, 'response content did not contain local media path'

    # verify files exist on disk
    # extract filenames
    parts = [p for p in content.split() if '/media/images/' in p]
    assert parts, 'no media paths found in content'
    root = Path(__file__).resolve().parent.parent
    from urllib.parse import urlparse
    for p in parts:
        p = p.strip().rstrip('.,')
        # parse URL and get the basename
        parsed = urlparse(p)
        name = Path(parsed.path).name
        fpath = root / 'media' / 'images' / name
        assert fpath.exists(), f'persisted image not found: {fpath}'
        # sidecar next to the image
        sidecar = fpath.with_suffix(fpath.suffix + '.json')
        assert sidecar.exists(), f'sidecar metadata missing: {sidecar}'
