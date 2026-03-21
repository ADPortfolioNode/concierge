"""Top-level lazy FastAPI entry for Vercel.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time.
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
        return


@app.get('/_health')
async def _health():
    return {"status": "ok"}
