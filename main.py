"""Top-level lazy FastAPI entry for Vercel.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time.
"""
from fastapi import FastAPI
import importlib
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
async def _mount_real_app():
    logger.info("startup: mounting real app...")
    try:
        real = importlib.import_module('app')
        real_app = getattr(real, 'app', None)
        if real_app is not None:
            app.mount('/', real_app)
            logger.info("mounted real app at '/'")
        else:
            logger.error("module 'app' has no attribute 'app' (real_app is None)")
    except Exception as e:
        logger.error(f"failed to import/mount real app: {e}")
        logger.error(traceback.format_exc())
        return

