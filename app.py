"""FastAPI application exposing the async SacredTimeline endpoint.

This app creates the necessary async components on startup and exposes a
single POST endpoint `/ask` which accepts JSON payload `{"input": "..."}`.
"""
from __future__ import annotations

import logging
import asyncio
import json
import traceback
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from config.settings import get_settings
from pathlib import Path

# Capability layers — plugins, tools, integrations
from plugins.plugin_loader import load_default_plugins
import plugins.plugin_registry as _plugin_reg
from integrations.integration_loader import load_default_integrations
import integrations.integration_registry as _intg_reg
from tools.tool_registry import list_tools as _list_tool_names, get_tool as _get_tool
from tools.tool_registry import register_tool as _register_tool

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


from pydantic import root_validator


class ConciergeMessagePayload(BaseModel):
    # legacy clients may send either `message` or `input`; normalize to
    # `message` for the rest of the code.
    message: Optional[str] = None
    input: Optional[str] = None

    @root_validator(pre=True)
    def require_one_field(cls, values):
        # prefer explicit "message" but fall back to "input" alias
        msg = values.get("message")
        if not msg and "input" in values:
            msg = values.get("input")
        if not msg or not isinstance(msg, str) or not msg.strip():
            raise ValueError("either 'message' or 'input' field must be provided and nonempty")
        values["message"] = msg
        return values


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

    # Register built-in tools so /api/v1/tools can list them
    from tools.web_search_tool import WebSearchTool
    from tools.code_execution_tool import CodeExecutionTool
    from tools.file_memory_tool import FileMemoryTool
    for tool_cls in (WebSearchTool, CodeExecutionTool, FileMemoryTool):
        try:
            _register_tool(tool_cls())
        except Exception:
            logger.exception("Failed to register built-in tool %r", tool_cls.__name__)

    # Load capability layers
    load_default_plugins()
    load_default_integrations()


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
    # the Pydantic validator above guarantees we have a nonempty `message`
    msg = payload.message
    result = await app.state.timeline.handle_user_input(msg)
    # The timeline may return a friendly conversational response in the
    # `response` field.  Convert that to the usual `content` string so the
    # frontend rendering logic (which looks at payload.content/text) works
    # correctly.
    content_val: Any
    if isinstance(result, dict) and "response" in result:
        content_val = result["response"]
    else:
        content_val = result
    try:
        # test serializability
        json.dumps(content_val)
    except Exception:
        content_val = str(content_val)

    data = {
        'id': str(int(__import__('time').time() * 1000)),
        'role': 'assistant',
        'content': content_val,
        # store the full timeline result in metadata so the frontend can
        # render a clean chat line while still retaining structured data for
        # inspection or UI widgets. downstream components should treat
        # `meta` as opaque and display it only when the user explicitly
        # expands or hovers.
        'meta': {'raw': result},
    }
    return _api_response(data)


@app.get('/api/v1/concierge/conversation')
async def concierge_conversation():
    # no persistent conversation in this simple server; return empty list
    return _api_response([])


# --- capability endpoints ---------------------------------------------------

@app.get('/api/v1/plugins')
async def get_plugins():
    """List all registered plugins and their metadata."""
    return _api_response(_plugin_reg.list_plugins())


@app.get('/api/v1/tools')
async def get_tools():
    """List all registered tools and their metadata."""
    names = _list_tool_names()
    serialized = []
    for name in names:
        tool = _get_tool(name)
        serialized.append({
            "name": name,
            "description": getattr(tool, "description", ""),
            "type": "tool",
        })
    return _api_response(serialized)


@app.get('/api/v1/integrations')
async def get_integrations():
    """List all registered integrations and their metadata."""
    return _api_response(_intg_reg.list_integrations())


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
