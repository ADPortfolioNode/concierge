import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='module')
def client():
    try:
        import main
    except Exception as exc:
        pytest.skip(f"Could not import main.py: {exc}")

    with TestClient(main.app) as client:
        yield client


def test_health_endpoints(client):
    resp = client.get('/_health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}

    resp = client.get('/api/_health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}

    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json().get('status') == 'ok'


def test_spa_fallback_serves_html(client):
    resp = client.get('/nonexistent-route')
    assert resp.status_code == 200
    assert '<!DOCTYPE html>' in resp.text
    assert '<div id="root"' in resp.text


def test_index_html_is_served(client):
    resp = client.get('/index.html')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers.get('content-type', '')
    assert '<!DOCTYPE html>' in resp.text


def test_assets_route_serves_static_file(client):
    asset_dir = ROOT / 'frontend' / 'dist' / 'assets'
    if not asset_dir.exists():
        pytest.skip('No built frontend assets found in frontend/dist/assets')

    # Choose a stable asset file name from the build output.
    candidates = [p.name for p in asset_dir.iterdir() if p.is_file() and p.name.startswith('index-')]
    assert candidates, 'No index asset file available for asset route regression test'

    asset_name = candidates[0]
    resp = client.get(f'/assets/{asset_name}')
    assert resp.status_code == 200
    assert 'text/html' not in resp.headers.get('content-type', '')
    assert resp.content


def test_missing_asset_returns_404(client):
    resp = client.get('/assets/this-asset-does-not-exist.js')
    assert resp.status_code == 404
