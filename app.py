"""FastAPI application exposing the async SacredTimeline endpoint.

This app creates the necessary async components on startup and exposes a
single POST endpoint `/ask` which accepts JSON payload `{"input": "..."}`.
"""
from __future__ import annotations

import logging
import asyncio
import json
import traceback
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from config.settings import get_settings
from pathlib import Path

# load application version from file
_VERSION_FILE = Path(__file__).parent / "VERSION"
try:
    VERSION = _VERSION_FILE.read_text().strip()
except Exception:
    VERSION = "unknown"

logging.basicConfig(level=logging.INFO)
app = FastAPI()
logger = logging.getLogger(__name__)
# log version on startup
logger.info(f"Concierge version {VERSION} starting")

# record application start for uptime measurements
import time
app.state.start_time = time.time()


# Simple request logging middleware to aid debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url)
    try:
        response = await call_next(request)
        logger.info("Response status: %s for %s %s", response.status_code, request.method, request.url)
        return response
    except Exception:
        logger.exception("Unhandled error in request middleware for %s %s", request.method, request.url)
        raise


# Global exception handler that returns the ApiResponse envelope with error details
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # catch-all ensures we always return JSON envelope even for unexpected errors
    logger.exception("Unhandled exception while handling request: %s %s", request.method, request.url)
    tb = traceback.format_exc()
    resp = _api_response(None, status='error')
    resp['errors'] = {
        'message': str(exc),
        'trace': tb.splitlines()[-20:],
    }
    code = 500
    if isinstance(exc, HTTPException):
        code = exc.status_code
    return JSONResponse(status_code=code, content=resp)


class AskPayload(BaseModel):
    input: str


class ConciergeMessagePayload(BaseModel):
    message: str


def _api_response(data: any, status: str = 'success'):
    from datetime import datetime
    return {
        'status': status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'request_id': str(int(datetime.utcnow().timestamp() * 1000)),
        'data': data,
        'meta': {
            'confidence': None,
            'priority': None,
            'media': None,
        },
        'errors': None,
    }


@app.on_event("startup")
async def _startup():
    # record the epoch time so we can report uptime later
    app.state.start_time = time.time()
    settings = get_settings()
    app.state.concurrency = AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
    app.state.memory = MemoryStore(collection_name=settings.memory_collection)
    app.state.timeline = SacredTimeline(concurrency_manager=app.state.concurrency, memory_store=app.state.memory)


# versioned endpoints are used by the frontend; we keep the old
# `/ask` path as an unversioned alias for compatibility but wrap all
# responses in our standard JSON envelope as well.  This makes it easier
# to relocate the logic under `/api/v1` later if desired.
@app.post("/ask")
async def ask(payload: AskPayload):
    if not payload.input:
        # return our error envelope rather than raw HTTPException
        return JSONResponse(status_code=400, content={
            "error": "input required",
            "code": 400,
        })
    result = await app.state.timeline.handle_user_input(payload.input)
    # wrap result to guarantee JSON output
    return JSONResponse(content={
        "response": result,
        "thread_id": None,
        "metadata": {},
    })


@app.post("/api/v1/concierge/message")
async def concierge_message(payload: ConciergeMessagePayload):
    if not payload.message:
        raise HTTPException(status_code=400, detail="message required")
    result = await app.state.timeline.handle_user_input(payload.message)
    # return in frontend-friendly ApiResponse envelope
    # Prefer returning structured objects so frontend can render them.
    # If the result is not JSON-serializable, fall back to its string form.
    content_val = result
    try:
        # test serializability
        json.dumps(result)
    except Exception:
        content_val = str(result)

    data = {
        'id': str(int(__import__('time').time() * 1000)),
        'role': 'assistant',
        'content': content_val,
    }
    return _api_response(data)


@app.get('/api/v1/concierge/conversation')
async def concierge_conversation():
    # no persistent conversation in this simple server; return empty list
    return _api_response([])



# --- health endpoints ------------------------------------------------------
@app.get('/health')
async def health():
    return JSONResponse(content={"status": "ok", "version": VERSION})

@app.get('/health/system')
async def health_system():
    # gather diagnostics without raising
    info: dict[str, Any] = {}
    # API obviously running
    info['api'] = 'ok'
    info['version'] = VERSION
    # uptime
    info['uptime_seconds'] = time.time() - getattr(app.state, 'start_time', time.time())
    # thread count
    try:
        import threading

        info['threads'] = threading.active_count()
    except Exception:
        info['threads'] = None
    # memory subsystem
    try:
        info['memory_graph'] = 'ok' if hasattr(app.state, 'memory') else 'unavailable'
    except Exception:
        info['memory_graph'] = 'error'
    # ping chroma and qdrant via memory store
    try:
        mem = app.state.memory
        if getattr(mem, '_client', None) is not None:
            # attempt a lightweight call depending on type
            if getattr(mem, '_is_qdrant', False):
                # qdrant ping
                try:
                    mem._client.get_collections()
                    info['qdrant'] = 'ok'
                except Exception:
                    info['qdrant'] = 'error'
                info['chroma'] = 'n/a'
            else:
                # chroma ping
                try:
                    # get or list collections
                    _ = mem._client.list_collections() if hasattr(mem._client, 'list_collections') else mem._client.get_collections()
                    info['chroma'] = 'ok'
                except Exception:
                    info['chroma'] = 'error'
                info['qdrant'] = 'n/a'
        else:
            info['chroma'] = 'unavailable'
            info['qdrant'] = 'unavailable'
    except Exception:
        info['chroma'] = 'error'
        info['qdrant'] = 'error'
    return JSONResponse(content=info)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
