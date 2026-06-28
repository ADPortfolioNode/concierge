import asyncio

from app import health_system, health_logs, app


def test_health_system_includes_log_count():
    # call the async function directly
    resp = asyncio.get_event_loop().run_until_complete(health_system())
    assert hasattr(resp, 'status_code') and resp.status_code == 200
    data = resp.body or {}
    # JSONResponse.body is bytes
    import json
    data = json.loads(resp.body)
    assert data.get("api") == "ok"
    assert "recent_log_lines" in data
    assert isinstance(data["recent_log_lines"], (int, type(None)))


def test_health_logs_returns_lines():
    # ensure there is at least one log entry by hitting system endpoint
    asyncio.get_event_loop().run_until_complete(health_system())
    r = asyncio.get_event_loop().run_until_complete(health_logs(limit=5))
    assert hasattr(r, 'status_code') and r.status_code == 200
    import json
    body = json.loads(r.body)
    assert "lines" in body
    assert isinstance(body["lines"], list)
    for line in body["lines"]:
        assert isinstance(line, str)
