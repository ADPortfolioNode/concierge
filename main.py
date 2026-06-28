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
<<<<<<< HEAD
=======
import traceback
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

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
<<<<<<< HEAD
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
=======
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
        raise


@app.on_event("shutdown")
async def _shutdown_real_app():
<<<<<<< HEAD
    # Lifespan is handled automatically on mount. No manual shutdown needed.
    logger.info("Root app shutdown. Mounted app shutdown is handled by the framework.")


@app.get('/_health')
async def _health():
    return {"status": "ok"}
=======
    real_app_lifespan = getattr(app.state, '_real_app_lifespan', None)
    if real_app_lifespan is not None:
        try:
            await real_app_lifespan.__aexit__(None, None, None)
            logger.info("real app lifecycle shutdown completed")
        except Exception:
            logger.exception("real app lifecycle shutdown failed")

>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
