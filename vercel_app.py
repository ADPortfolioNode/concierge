"""Minimal FastAPI entry for Vercel detection.

Defines a very small `app` instance (no heavy imports at module import
time). On startup it will attempt to import and mount the real
application so runtime behavior is unchanged while keeping build-time
imports cheap and predictable.
"""
from fastapi import FastAPI

app = FastAPI()


@app.on_event("startup")
async def _mount_real_app():
    try:
        import importlib
        real = importlib.import_module('app')
        real_app = getattr(real, 'app', None)
        if real_app is not None:
            app.mount('/', real_app)
    except Exception:
        # swallow; if mounting fails runtime logs will show details
        return


@app.get('/_health')
async def _health():
    return {"status": "ok"}
