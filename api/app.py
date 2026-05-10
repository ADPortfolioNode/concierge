"""Fallback API entrypoint to satisfy Vercel's FastAPI detection.

This defines a small `app` instance (static) and attempts to mount the
real application from the project's top-level `app` module if available.
Mounting keeps the lightweight `app` symbol in this file so the builder
can detect a FastAPI entrypoint without importing large modules at
parse-time.
"""
from fastapi import FastAPI

app = FastAPI()


@app.on_event("startup")
async def _try_mount_real_app():
    # Import the heavier application lazily at runtime (startup) so the
    # builder can detect this lightweight `app` without importing the
    # full project during the build phase.
    try:
        import importlib
        real = importlib.import_module('app')
        real_app = getattr(real, 'app', None)
        if real_app is not None:
            app.mount("/", real_app)
    except Exception:
        # swallow errors here; runtime logs will show details if needed
        return


@app.get('/_health')
async def _health():
    return {"status": "ok"}
