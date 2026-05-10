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
            app.state._real_app = real_app
            app.state._real_app_lifespan = real_app.router.lifespan_context(real_app)
            logger.info("mounted real app at '/'")
            try:
                await app.state._real_app_lifespan.__aenter__()
                logger.info("real app lifecycle startup completed")
            except Exception as startup_exc:
                logger.error("real app lifecycle startup failed: %s", startup_exc)
                logger.error(traceback.format_exc())
                raise
        else:
            logger.error("module 'app' has no attribute 'app' (real_app is None)")
            raise RuntimeError("real app missing")
    except Exception as e:
        logger.error(f"failed to import/mount real app: {e}")
        logger.error(traceback.format_exc())
        raise


@app.on_event("shutdown")
async def _shutdown_real_app():
    real_app_lifespan = getattr(app.state, '_real_app_lifespan', None)
    if real_app_lifespan is not None:
        try:
            await real_app_lifespan.__aexit__(None, None, None)
            logger.info("real app lifecycle shutdown completed")
        except Exception:
            logger.exception("real app lifecycle shutdown failed")

