"""Minimal observability helpers: Prometheus metrics and OpenTelemetry starter.

Provides:
- `setup(app)` to register a `/metrics` endpoint and request counter middleware.
"""
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from typing import Callable
from fastapi import Request, Response

REQUEST_COUNTER = Counter('concierge_http_requests_total', 'Total HTTP requests', ['method', 'path', 'status'])
MEDIA_SAVED = Counter('concierge_media_saved_total', 'Total media files saved')


def _metrics_endpoint() -> Response:
    registry = CollectorRegistry()
    # Default registry is used by Counters; generate_latest without registry
    # will include our counters by default.
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def setup(app) -> None:
    # add /metrics route
    try:
        app.add_api_route('/metrics', lambda: _metrics_endpoint(), methods=['GET'])
    except Exception:
        pass

    # NOTE: Request counting middleware is intentionally NOT added here
    # because adding middleware after the app has started raises an error
    # in some hosting environments. Instead, callers should increment
    # `REQUEST_COUNTER` from their existing request middleware.
