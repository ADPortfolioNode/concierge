"""Minimal FastAPI entry for Vercel detection.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time. On startup it will attempt to import and mount the real
application so runtime behavior is unchanged while keeping build-time
imports cheap and predictable.
"""
from fastapi import FastAPI
import importlib
import logging

logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
async def _mount_real_app():
    try:
        real = importlib.import_module('app')
        real_app = getattr(real, 'app', None)
        if real_app is not None:
            # Mount the real application. FastAPI/Starlette will automatically
            # handle the lifespan events (startup/shutdown) of the mounted app.
            app.mount('/', real_app)
            app.state._real_app = real_app
        else:
            raise RuntimeError("Failed to find 'app' attribute in 'app' module.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to import and mount real application: {e}", exc_info=True)
        logger.critical(
            "This usually means the main 'app.py' has an error (e.g., a syntax error or a missing dependency). "
            "Check the traceback above. For local debugging, try running 'uvicorn app:app --reload' directly "
            "to get a more direct error message."
        )
        # Re-raising the exception is crucial to prevent the server
        # from starting in a broken state.
        raise


@app.on_event("shutdown")
async def _shutdown_real_app():
    # Lifespan is handled automatically on mount. No manual shutdown needed.
    logger.info("Root app shutdown. Mounted app shutdown is handled by the framework.")


@app.get('/_health')
async def _health():
    return {"status": "ok"}
