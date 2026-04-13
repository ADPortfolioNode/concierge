import importlib

from fastapi.testclient import TestClient


def _reload_app_with_cors_origins(monkeypatch, cors_allow_origins: str):
    # Ensure env vars take precedence and avoid reloading .env values from the app module.
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", cors_allow_origins)
    try:
        import dotenv

        monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)
    except ImportError:
        pass

    return importlib.reload(importlib.import_module("app")).app


def _cors_preflight(client: TestClient, origin: str):
    return client.options(
        "/api/v1/concierge/timeline",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )


def test_cors_allows_local_dev_origin(monkeypatch):
    app = _reload_app_with_cors_origins(
        monkeypatch,
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    with TestClient(app) as client:
        resp = _cors_preflight(client, "http://localhost:5173")
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert resp.headers["access-control-allow-credentials"] == "true"
        assert "GET" in resp.headers["access-control-allow-methods"]


def test_cors_allows_production_origin(monkeypatch):
    app = _reload_app_with_cors_origins(
        monkeypatch,
        "https://deoismconcierge.vercel.app,https://deoismconcierge-adportfolionodes-projects.vercel.app",
    )
    with TestClient(app) as client:
        resp = _cors_preflight(client, "https://deoismconcierge.vercel.app")
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "https://deoismconcierge.vercel.app"
        assert resp.headers["access-control-allow-credentials"] == "true"
        assert "GET" in resp.headers["access-control-allow-methods"]
