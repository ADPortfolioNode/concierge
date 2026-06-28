from fastapi.testclient import TestClient

from app import app


def test_stream_endpoint_options_allows_preflight():
    client = TestClient(app)
    resp = client.options('/api/v1/concierge/stream')
    assert resp.status_code == 200
