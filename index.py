"""Lightweight FastAPI entry wrapper for Vercel.

Avoid importing the project's heavy `app` module at import-time so the
builder can detect a top-level `app` symbol without executing expensive
initialization. The real application is mounted at startup.
"""
import logging
from fastapi import FastAPI

# Start with a known top-level app for Vercel detection.
app = FastAPI()

try:
    # main.py provides the full app (API + SPA fallback) and is prioritized
    from main import app as main_app
    app = main_app
except Exception:
    # gracefully fallback to the previous lazy mount behavior if main is unavailable.
    @app.on_event("startup")
    async def _mount_real_app():
        try:
            import importlib
            real = importlib.import_module('app')
            real_app = getattr(real, 'app', None)
            if real_app is not None:
                app.mount('/', real_app)
        except Exception:
            return

    @app.get('/_health')
    async def _health():
        return {"status": "ok"}

