"""FastAPI application exposing the async SacredTimeline endpoint.

This app creates the necessary async components on startup and exposes a
single POST endpoint `/ask` which accepts JSON payload `{"input": "..."}`.
"""
from __future__ import annotations

import logging
import asyncio
import json
import os
import time
import traceback
import uuid
from typing import Any, Optional, Deque
from pathlib import Path
from config.settings import get_settings
import collections

# Load .env before any os.getenv calls so keys are available to all modules.
# Use override=True so local .env explicitly governs values during development
# (won't affect CI if env vars are provided by the environment).
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).parent / ".env", override=True)
except ImportError:
    # If python-dotenv isn't available, try a minimal manual loader for the
    # most common keys so running from PowerShell/Git Bash still works.
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            for ln in env_path.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if not ln or ln.startswith('#') or '=' not in ln:
                    continue
                k, v = ln.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # prefer explicit .env value; always set so child processes see it
                os.environ[k] = v
        except Exception:
            pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse, Response, HTMLResponse, FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx
import hashlib
import re
from datetime import datetime
from jobs.task_tree_store import get_redis, get_task_tree

# Defer heavy/optional imports to runtime to keep module import small for
# serverless builds. Populate these in the lifespan startup.
SacredTimeline = None
AsyncConcurrencyManager = None
MemoryStore = None

# capability layers placeholders
load_default_plugins = None
_plugin_reg = None
load_default_integrations = None
_intg_reg = None
_list_tool_names = None
_get_tool = None
_register_tool = None
is_enabled = None
observability_setup = None
MEDIA_SAVED = None
REQUEST_COUNTER = None

# routers / task handlers placeholders
_upload_router = None
_project_router = None
_task_router = None
_get_task_queue = None
_register_task_handlers = None
_job_router = None
_jobs_available = False
_jobs_import_err_msg = None

# load application version from file
_VERSION_FILE = Path(__file__).parent / "VERSION"
try:
    VERSION = _VERSION_FILE.read_text().strip()
except Exception:
    VERSION = "unknown"

logging.basicConfig(level=logging.INFO)
# --- recent-log handler ----------------------------------------------------
class _RecentLogHandler(logging.Handler):
    """Keep the last *n* formatted log lines in memory for monitoring endpoints."""
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.deque: Deque[str] = collections.deque(maxlen=capacity)
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.deque.append(self.format(record))
        except Exception:
            pass

_recent_logs = _RecentLogHandler(capacity=int(os.getenv("RECENT_LOG_CAP", "500")))
_recent_logs.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.getLogger().addHandler(_recent_logs)

logger = logging.getLogger(__name__)
# log version on startup
logger.info(f"Concierge version {VERSION} starting")
# Log presence of key environment variables (don't print secrets)
_openai_set = bool(os.getenv("OPENAI_API_KEY"))
_gemini_set = bool(os.getenv("GEMINI_API_KEY"))
logger.info(f"OPENAI_API_KEY set: {_openai_set}; GEMINI_API_KEY set: {_gemini_set}")
if not _jobs_available and _jobs_import_err_msg:
    logger.warning("Distributed jobs layer unavailable: %s", _jobs_import_err_msg)

settings = get_settings()
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8001')


@asynccontextmanager
async def _lifespan(application: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────
    application.state.start_time = time.time()
    application.state.conversation = []  # in-memory history; cleared on restart
    import importlib
    global is_enabled
    # late-import configuration and core components
    cfg_mod = importlib.import_module('config.settings')
    settings = cfg_mod.get_settings()

    concurrency_mod = importlib.import_module('core.concurrency')
    AsyncConcurrencyManager = getattr(concurrency_mod, 'AsyncConcurrencyManager')

    memory_mod = importlib.import_module('memory.memory_store')
    MemoryStore = getattr(memory_mod, 'MemoryStore')

    orches_mod = importlib.import_module('orchestration.sacred_timeline')
    SacredTimeline = getattr(orches_mod, 'SacredTimeline')

    # optional LLM wrapper for memory embedding support
    llm_tool = None
    try:
        llm_mod = importlib.import_module('tools.llm_tool')
        llm_cls = getattr(llm_mod, 'LLMTool')
        llm_tool = llm_cls()
    except Exception:
        llm_tool = None

    # feature flag helper (populate module-level `is_enabled` so route handlers
    # can call it without requiring imports)
    try:
        ff_mod = importlib.import_module('core.feature_flags')
        is_enabled = getattr(ff_mod, 'is_enabled')
    except Exception:
        is_enabled = lambda name: False

    application.state.concurrency = AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
    application.state.memory = MemoryStore(collection_name=settings.memory_collection, llm_tool=llm_tool)
    application.state.timeline = SacredTimeline(
        concurrency_manager=application.state.concurrency,
        memory_store=application.state.memory,
    )
    # start background media cleanup task
    async def _media_cleanup_loop():
        try:
            media_images = settings.media_images_dir
            max_age = settings.media_max_age_seconds
            while True:
                try:
                    now = time.time()
                    if media_images.exists():
                        for p in media_images.iterdir():
                            try:
                                if p.is_file():
                                    mtime = p.stat().st_mtime
                                    if now - mtime > max_age:
                                        p.unlink()
                            except Exception:
                                logger.exception('Failed to evaluate/remove media file %s', p)
                except Exception:
                    logger.exception('Media cleanup iteration failed')
                await asyncio.sleep(int(os.getenv('MEDIA_CLEANUP_INTERVAL', '3600')))
        except asyncio.CancelledError:
            return

    application.state.media_cleanup_task = asyncio.create_task(_media_cleanup_loop())
    # attach observability endpoints and middleware (lazy import)
    try:
        obs_mod = importlib.import_module('core.observability')
        observability_setup = getattr(obs_mod, 'setup')
        MEDIA_SAVED = getattr(obs_mod, 'MEDIA_SAVED', None)
        REQUEST_COUNTER = getattr(obs_mod, 'REQUEST_COUNTER', None)
        observability_setup(application)
    except Exception:
        logger.exception('Failed to initialize observability')
    # Register built-in tools
    try:
        tools_mod = importlib.import_module('tools.tool_registry')
        _register_tool = getattr(tools_mod, 'register_tool')
        _list_tool_names = getattr(tools_mod, 'list_tools')
        _get_tool = getattr(tools_mod, 'get_tool')
    except Exception:
        _register_tool = None
        _list_tool_names = None
        _get_tool = None

    try:
        from tools.web_search_tool import WebSearchTool
        from tools.code_execution_tool import CodeExecutionTool
        from tools.file_memory_tool import FileMemoryTool
        for tool_cls in (WebSearchTool, CodeExecutionTool, FileMemoryTool):
            try:
                if _register_tool:
                    _register_tool(tool_cls())
            except Exception:
                logger.exception("Failed to register built-in tool %r", tool_cls.__name__)
    except Exception:
        # tools optional for minimal deployments
        pass

    # Load capability layers (plugins/integrations)
    try:
        pl_mod = importlib.import_module('plugins.plugin_loader')
        load_default_plugins = getattr(pl_mod, 'load_default_plugins')
        pr_mod = importlib.import_module('plugins.plugin_registry')
        _plugin_reg = pr_mod
        if load_default_plugins:
            load_default_plugins()
    except Exception:
        logger.exception('Failed to load plugins (continuing)')

    try:
        il_mod = importlib.import_module('integrations.integration_loader')
        load_default_integrations = getattr(il_mod, 'load_default_integrations')
        ir_mod = importlib.import_module('integrations.integration_registry')
        _intg_reg = ir_mod
        if load_default_integrations:
            load_default_integrations()
    except Exception:
        logger.exception('Failed to load integrations (continuing)')

    # Wire file-agent handlers and start the background task worker (optional)
    try:
        tw_mod = importlib.import_module('tasks.task_worker')
        _register_task_handlers = getattr(tw_mod, 'register_default_handlers')
        tq_mod = importlib.import_module('tasks')
        _get_task_queue = getattr(tq_mod, 'get_queue')
        _register_task_handlers()
        await _get_task_queue().start_worker()
    except Exception:
        logger.exception('Task worker not available or failed to start (continuing)')

    # Register routers from workstation/projects/tasks if available
    try:
        ws_mod = importlib.import_module('workstation')
        _upload_router = getattr(ws_mod, 'upload_router', None)
        if _upload_router is not None:
            application.include_router(_upload_router)
    except Exception:
        pass
    try:
        prj_mod = importlib.import_module('projects')
        _project_router = getattr(prj_mod, 'project_router', None)
        if _project_router is not None:
            application.include_router(_project_router)
    except Exception:
        pass
    try:
        tmod = importlib.import_module('tasks')
        _task_router = getattr(tmod, 'task_router', None)
        if _task_router is not None:
            application.include_router(_task_router)
    except Exception:
        pass

    # Optional distributed job router
    try:
        jr_mod = importlib.import_module('jobs.job_router')
        _job_router = getattr(jr_mod, 'router', jr_mod)
        _jobs_available = True
        if _job_router is not None:
            application.include_router(_job_router)
    except Exception as _jobs_import_err:  # noqa: BLE001
        _job_router = None
        _jobs_available = False
        _jobs_import_err_msg = str(_jobs_import_err)
    yield
    # ── shutdown (nothing to clean up yet) ───────────────────────────────


app = FastAPI(lifespan=_lifespan)

from fastapi.middleware.cors import CORSMiddleware

# CORS configuration is driven by a single source: CORS_ALLOW_ORIGINS.
# If unset, we fall back to the legacy allowed origins used by local dev
# and production deployments.

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://deoismconcierge.vercel.app",
    "https://deoismconcierge-adportfolionodes-projects.vercel.app",
]

_LOCALHOST_CORS_ALIASES = {
    "http://localhost:5173": "http://127.0.0.1:5173",
    "http://127.0.0.1:5173": "http://localhost:5173",
}


def _parse_cors_allow_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    origins = []
    for part in raw_value.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.append(origin)
    return origins


def _expand_cors_origin_aliases(origins: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for origin in origins:
        if origin in seen:
            continue
        seen.add(origin)
        expanded.append(origin)
        alias = _LOCALHOST_CORS_ALIASES.get(origin)
        if alias and alias not in seen:
            seen.add(alias)
            expanded.append(alias)
    return expanded


def _get_cors_origins() -> list[str]:
    env_origins = _parse_cors_allow_origins(os.getenv("CORS_ALLOW_ORIGINS"))
    if not env_origins:
        return _DEFAULT_CORS_ORIGINS.copy()

    return _expand_cors_origin_aliases(env_origins)


# CORS middleware for local React frontend on port 5173 calling backend on 8001
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated media (images/audio/video) from /media
try:
    media_path = settings.media_dir
    try:
        media_path.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=str(media_path)), name="media")
    except OSError as _err:
        import errno as _errno
        # On serverless platforms the package directory may be read-only.
        # Fall back to a writable temporary directory, preferably explicit
        # MEDIA_DIR_FALLBACK or `/tmp/media`.
        if getattr(_err, 'errno', None) == _errno.EROFS or getattr(_err, 'errno', None) == 30:
            tmp_media = settings.media_fallback_dir
            if not tmp_media.is_absolute():
                tmp_media = Path('/tmp') / tmp_media
            try:
                tmp_media.mkdir(parents=True, exist_ok=True)
                settings.media_dir = tmp_media
                settings.media_images_dir = tmp_media / 'images'
                app.mount("/media", StaticFiles(directory=str(tmp_media)), name="media")
                logger.warning("Read-only filesystem; using fallback media dir: %s", tmp_media)
            except Exception:
                logger.exception("Failed to create or mount fallback media directory %s", tmp_media)
        else:
            raise
except Exception:
    logger.exception("Failed to mount media directory for static files")

# Simple request logging middleware to aid debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url)
    try:
        response = await call_next(request)
        # increment Prometheus request counter if available
        try:
            REQUEST_COUNTER.labels(method=request.method, path=request.url.path, status=str(response.status_code)).inc()
        except Exception:
            pass
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


from pydantic import model_validator


class ConciergeMessagePayload(BaseModel):
    # legacy clients may send either `message` or `input`; normalize to
    # `message` for the rest of the code.
    message: Optional[str] = None
    input: Optional[str] = None
    # Optional full conversation history from the browser (IndexedDB-backed).
    # This enables the hybrid memory pattern: browser stores the chat thread;
    # backend receives full context on every call for richer RAG retrieval.
    history: Optional[list] = None

    @model_validator(mode='before')
    @classmethod
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
            # information about the LLM provider used for this response, if
            # applicable.  ``provider`` can be ``openai``, ``gemini`` or
            # ``rule-based``, and ``error`` carries any fallback message.
            'llm': {'provider': None, 'error': None},
        },
        'errors': None,
    }


def _ensure_timeline_available():
    """Raise HTTP 503 if the application's timeline component is not ready.

    Some serverless deployments may mount the app before background
    components initialize; guard endpoints that rely on `app.state.timeline`
    so they return a 503 (service temporarily unavailable) instead of
    raising an AttributeError and producing a 500.
    """
    if not hasattr(app.state, 'timeline') or app.state.timeline is None:
        raise HTTPException(status_code=503, detail='service temporarily unavailable')


def _find_task_node(tree: Any, task_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(tree, dict):
        return None
    if tree.get("task_id") == task_id:
        return tree
    for child in tree.get("children", []) or []:
        found = _find_task_node(child, task_id)
        if found is not None:
            return found
    return None


# startup logic moved to _lifespan context manager above


# versioned endpoints are used by the frontend; we keep the old
# `/ask` path as an unversioned alias for compatibility but wrap all
# responses in our standard JSON envelope as well.  This makes it easier
# to relocate the logic under `/api/v1` later if desired.
@app.post("/ask")
async def ask(payload: AskPayload):
    _ensure_timeline_available()
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


@app.post('/api/v1/concierge/message')
async def concierge_message(payload: ConciergeMessagePayload, request: Request):
    return await _handle_chat_message(payload, request)


@app.post('/chat')
async def chat_alias(payload: ConciergeMessagePayload, request: Request):
    """Legacy compatibility alias. The canonical endpoint is /api/v1/concierge/message."""
    return await _handle_chat_message(payload, request)


async def _handle_chat_message(payload: ConciergeMessagePayload, request: Request):
    # the Pydantic validator above guarantees we have a nonempty `message`
    msg = payload.message
    _ensure_timeline_available()
    thread_id = str(uuid.uuid4())
    result = await app.state.timeline.handle_user_input(msg, thread_id=thread_id)
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

    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    user_entry = {'id': str(int(time.time() * 1000) - 1), 'role': 'user', 'content': msg, 'timestamp': now}
    data = {
        'id': str(int(time.time() * 1000)),
        'role': 'assistant',
        'content': content_val,
        # store the full timeline result in metadata so the frontend can
        # render a clean chat line while still retaining structured data for
        # inspection or UI widgets. downstream components should treat
        # `meta` as opaque and display it only when the user explicitly
        # expands or hovers.
        'meta': {'raw': result},
        'timestamp': now,
    }

    # Persist any remote images found in the assistant response and rewrite
    # their URLs to point at our local `/media/images/` mount so the frontend
    # always renders a stable, local copy.
    def _request_base_url(request: Request) -> str:
        forwarded_proto = request.headers.get('x-forwarded-proto') or request.headers.get('x-forwarded-protocol')
        forwarded_host = request.headers.get('x-forwarded-host') or request.headers.get('host')
        if forwarded_proto and forwarded_host:
            return f"{forwarded_proto.rstrip('://')}://{forwarded_host}"
        if forwarded_host:
            scheme = request.url.scheme or 'https'
            return f"{scheme}://{forwarded_host}"
        return str(request.base_url).rstrip('/')

    async def _persist_and_rewrite_images(text: str, request: Request) -> str:
        if not text or not isinstance(text, str):
            return text
        # simple heuristic: match http/https URLs that likely point to images
        url_re = re.compile(r"(https?://[^\s\)\"]+\.(?:png|jpe?g|gif|webp))", re.IGNORECASE)
        found = list(url_re.finditer(text))
        if not found:
            # try a looser match (no extension) and check content-type
            url_re2 = re.compile(r"(https?://[^\s\)\"]+)")
            candidates = [m.group(1) for m in url_re2.finditer(text)]
        else:
            candidates = [m.group(1) for m in found]

        media_dir = settings.media_images_dir
        media_dir.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in candidates:
                try:
                    # HEAD first to check content-type quickly
                    head = await client.head(url, follow_redirects=True)
                    ctype = head.headers.get('content-type', '') if head is not None else ''
                    if not ctype.startswith('image'):
                        # try GET anyway for some hosts that don't respond to HEAD
                        resp = await client.get(url, follow_redirects=True)
                        if resp.status_code != 200 or not resp.headers.get('content-type', '').startswith('image'):
                            continue
                    else:
                        resp = await client.get(url, follow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    img_bytes = resp.content
                    # derive extension from content-type or url
                    ext = None
                    if 'jpeg' in resp.headers.get('content-type', ''):
                        ext = 'jpg'
                    elif 'png' in resp.headers.get('content-type', ''):
                        ext = 'png'
                    elif 'gif' in resp.headers.get('content-type', ''):
                        ext = 'gif'
                    elif 'webp' in resp.headers.get('content-type', ''):
                        ext = 'webp'
                    else:
                        # fallback: try to take extension from URL
                        parsed = url.split('?')[0]
                        if '.' in parsed:
                            ext = parsed.rsplit('.', 1)[-1][:4]
                        else:
                            ext = 'png'
                    # filename deterministic-ish
                    sha = hashlib.sha1(img_bytes).hexdigest()[:12]
                    ts = int(time.time())
                    fname = f"img_{sha}_{ts}.{ext}"
                    fpath = media_dir / fname
                    fpath.write_bytes(img_bytes)
                    # sidecar metadata
                    sidecar = {
                        'filename': fname,
                        'prompt': None,
                        'mime_type': resp.headers.get('content-type', ''),
                        'created_at': datetime.utcnow().isoformat() + 'Z',
                        'size': len(img_bytes),
                        'source': 'remote',
                        'remote_url': url,
                    }
                    try:
                        (media_dir / (fname + '.json')).write_text(json.dumps(sidecar))
                    except Exception:
                        logger.exception('Failed to write sidecar for %s', fname)
                    # replace occurrences of the original URL with our local path
                    if is_enabled('media_absolute_urls'):
                        try:
                            base = _request_base_url(request)
                            local_url = f"{base}/media/images/{fname}"
                        except Exception:
                            local_url = f"/media/images/{fname}"
                    else:
                        local_url = f"/media/images/{fname}"
                    text = text.replace(url, local_url)
                except Exception:
                    logger.exception('Failed to fetch or persist image %s', url)
                    continue
        return text

    # rewrite content_val and raw metadata if they contain remote image URLs
    try:
        content_val = await _persist_and_rewrite_images(content_val, request)
    except Exception:
        logger.exception('Error persisting images found in assistant content')
    try:
        # if result is a dict/structured object, stringify nested response text
        if isinstance(result, dict):
            # deep scan for strings in result to rewrite URLs
            def _rewrite_in_obj(obj):
                if isinstance(obj, str):
                    return asyncio.get_event_loop().run_until_complete(_persist_and_rewrite_images(obj))
                if isinstance(obj, dict):
                    return {k: _rewrite_in_obj(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_rewrite_in_obj(v) for v in obj]
                return obj
            try:
                # run the rewrite for top-level known keys
                if 'response' in result and isinstance(result['response'], str):
                    result['response'] = await _persist_and_rewrite_images(result['response'], request)
                if 'media' in result and isinstance(result['media'], list):
                    new_media = []
                    for m in result['media']:
                        if isinstance(m, str):
                            new_media.append(await _persist_and_rewrite_images(m, request))
                        elif isinstance(m, dict):
                            # rewrite url fields inside media dicts
                            if 'url' in m and isinstance(m['url'], str):
                                m['url'] = await _persist_and_rewrite_images(m['url'], request)
                            new_media.append(m)
                    result['media'] = new_media
            except Exception:
                logger.exception('Failed to rewrite nested URLs in result dict')
    except Exception:
        logger.exception('Error scanning result for images')

    # append entries to conversation state (used by /conversation endpoint)
    app.state.conversation.append(user_entry)
    app.state.conversation.append(data)

    # build the API response envelope and copy provider/error info into meta
    resp = _api_response(data)
    resp['thread_id'] = thread_id
    llm_meta = resp['meta'].get('llm')
    if llm_meta is not None and isinstance(result, dict):
        llm_meta['provider'] = result.get('llm_provider')
        llm_meta['error'] = result.get('llm_error')
    return resp


@app.get('/api/v1/concierge/metrics')
async def concierge_metrics():
    """Return simple human-readable metrics about request handling and fallbacks."""
    _ensure_timeline_available()
    metrics = getattr(app.state.timeline, 'metrics', None)
    if metrics is None:
        return _api_response({'error': 'metrics not available'}, status='error')
    # Copy values for API
    m = {
        'total_requests': metrics.total_requests,
        'requests_queued': metrics.requests_queued,
        'failovers': metrics.failovers,
        'summary': f"{metrics.total_requests} requests processed, {metrics.requests_queued} queued, {metrics.failovers} fallbacks to alternate LLM."
    }
    return _api_response(m)


# timeline introspection endpoints
@app.get('/api/v1/concierge/timeline')
async def concierge_timeline():
    _ensure_timeline_available()
    try:
        plan = app.state.timeline.get_last_plan()
        return _api_response(plan or {})
    except Exception:
        logger.exception('Failed to fetch timeline plan')
        return _api_response({'error': 'timeline plan unavailable'}, status='error')

@app.get('/api/v1/tasks')
async def list_tasks():
    try:
        client = get_redis()
        task_keys = list(client.scan_iter(match='task_tree:*', count=100))
        tasks = []
        for key in task_keys:
            thread_id = key.split(':', 1)[1] if ':' in key else key
            task_tree = get_task_tree(thread_id)
            if not task_tree:
                continue
            metadata = task_tree.get('metadata') or {}
            tasks.append({
                'id': thread_id,
                'type': metadata.get('task_type') or task_tree.get('task_name') or thread_id,
                'status': task_tree.get('status') or task_tree.get('state') or 'unknown',
                'created_at': None if metadata.get('start_time') is None else datetime.fromtimestamp(float(metadata.get('start_time'))).isoformat(),
            })
        tasks.sort(key=lambda item: item.get('created_at') or '', reverse=True)
        return _api_response(tasks)
    except Exception:
        logger.exception('Failed to fetch task list')
        return _api_response({'error': 'task list unavailable'}, status='error')

@app.get('/api/v1/tasks/{task_id}/status')
async def task_status(task_id: str):
    try:
        task_tree = get_task_tree(task_id)
    except Exception as exc:
        logger.exception('Failed to fetch task status for %s', task_id)
        resp = _api_response(None, status='error')
        resp['errors'] = {'message': str(exc)}
        return JSONResponse(status_code=503, content=resp)

    if task_tree is None:
        raise HTTPException(status_code=404, detail='task_id not found')
    return _api_response(task_tree)

@app.get('/api/v1/concierge/timeline/graph')
async def concierge_timeline_graph():
    _ensure_timeline_available()
    try:
        png = app.state.timeline.get_plan_graph_png()
        return StreamingResponse(iter([png]), media_type='image/png')
    except Exception:
        logger.exception('Failed to generate timeline graph')
        return StreamingResponse(iter([b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x04\x00\x01\x0e\x11\x02\xb5\x00\x00\x00\x00IEND\xaeB`\x82']), media_type='image/png')


@app.get('/api/v1/concierge/timeline/stream')
async def concierge_timeline_stream(thread_id: Optional[str] = None):
    """Server-Sent Events endpoint streaming timeline updates in real-time.

    Each event is a structured delta object and may include visual graph hints
    for the frontend visualizer: node_add, node_update, edge_add, task_update,
    and plan metadata.
    """
    async def event_generator():
        _ensure_timeline_available()
        q = app.state.timeline.subscribe_timeline()
        try:
            while True:
                update = await q.get()
                import json as _json
                update_thread_id = update.get("thread_id") if isinstance(update, dict) else None
                if thread_id and update_thread_id and update_thread_id != thread_id:
                    continue
                yield f"data: {_json.dumps(update)}\n\n"
        finally:
            try:
                app.state.timeline.unsubscribe_timeline(q)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type='text/event-stream')

@app.websocket('/api/v1/concierge/timeline/ws')
async def concierge_timeline_websocket(websocket: WebSocket):
    await websocket.accept()
    _ensure_timeline_available()
    thread_id = websocket.query_params.get("thread_id")
    q = app.state.timeline.subscribe_timeline()
    try:
        while True:
            update = await q.get()
            update_thread_id = update.get("thread_id") if isinstance(update, dict) else None
            if thread_id and update_thread_id and update_thread_id != thread_id:
                continue
            await websocket.send_json(update)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception('Timeline websocket error')
    finally:
        try:
            app.state.timeline.unsubscribe_timeline(q)
        except Exception:
            pass


@app.get('/api/v1/concierge/threads/{thread_id}/nodes/{node_id}/memories')
async def concierge_node_memories(thread_id: str, node_id: str, top_k: int = 8):
    """Return memory snippets related to a thread node for visualizer side panels."""
    _ensure_timeline_available()
    if top_k < 1:
        top_k = 1
    if top_k > 20:
        top_k = 20

    task_tree = get_task_tree(thread_id)
    if task_tree is None:
        raise HTTPException(status_code=404, detail='thread_id not found')

    node = _find_task_node(task_tree, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail='node_id not found')

    context_parts = [node_id]
    if isinstance(node, dict):
        task_name = node.get("task_name")
        if isinstance(task_name, str) and task_name.strip():
            context_parts.append(task_name.strip())
        metadata = node.get("metadata")
        if isinstance(metadata, dict):
            if isinstance(metadata.get("result_summary"), str):
                context_parts.append(metadata["result_summary"])
            if isinstance(metadata.get("tool_name"), str):
                context_parts.append(metadata["tool_name"])
            if isinstance(metadata.get("agent_type"), str):
                context_parts.append(metadata["agent_type"])
    context = " ".join(context_parts).strip()

    memories = await app.state.memory.query(context=context, top_k=top_k)
    ranked = []
    for idx, memory in enumerate(memories):
        score = None
        if isinstance(memory, dict):
            score = memory.get("score")
            if not isinstance(score, (int, float)):
                score = max(0.1, 1 - (idx / max(len(memories), 1)))
            ranked.append({
                "id": str(memory.get("id", f"mem-{idx}")),
                "summary": str(memory.get("summary", "")),
                "score": float(score),
                "metadata": memory.get("metadata", {}),
            })
    return _api_response({"thread_id": thread_id, "node_id": node_id, "memories": ranked})


async def _create_concierge_stream_response(message: str, thread_id: Optional[str] = None) -> StreamingResponse:
    _ensure_timeline_available()

    if thread_id is None:
        thread_id = str(uuid.uuid4())

    async def _event_gen():
        try:
            async for evt_json in app.state.timeline.stream_user_input(message, thread_id=thread_id):
                yield f"data: {evt_json}\n\n"
        except Exception as exc:
            logger.exception("SSE stream error")
            import json as _j
            yield f"data: {_j.dumps({'type': 'error', 'text': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx proxy buffering
            "Connection": "keep-alive",
        },
    )


@app.post('/api/v1/concierge/stream')
async def concierge_stream(payload: ConciergeMessagePayload):
    """Server-Sent Events endpoint — streams tokens as they are produced by the LLM.

    Each SSE event carries a JSON-encoded dict.  See
    ``SacredTimeline.stream_user_input`` for the event shapes.

    The client should open this with ``fetch`` + ``ReadableStream`` (or
    an ``EventSource`` that supports POST — most libraries do).
    """
    return await _create_concierge_stream_response(payload.message)


@app.get('/api/v1/concierge/stream')
async def concierge_stream_get(message: str):
    """Compatibility GET endpoint for stream clients that cannot POST."""
    return await _create_concierge_stream_response(message)


@app.options('/api/v1/concierge/stream')
async def concierge_stream_options():
    """Support preflight checks for streaming clients."""
    return Response(status_code=200)


@app.get('/api/v1/concierge/conversation')
async def concierge_conversation():
    return _api_response(list(app.state.conversation))


@app.get('/api/v1/concierge/media')
async def concierge_media_list(request: Request):
    """Admin listing of saved media files (media/images)."""
    try:
        media_images = settings.media_images_dir
        items = []
        if media_images.exists():
            # Only include image files (skip sidecar JSON files)
            allowed_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif'}
            for p in sorted(media_images.iterdir()):
                if p.is_file() and p.suffix.lower() in allowed_exts:
                    stat = p.stat()
                    # If feature flag `media_absolute_urls` is enabled, return
                    # absolute URLs based on the request base URL so clients
                    # do not need to normalize `/media` paths.
                    try:
                        base_url = str(request.scope.get('root_path', ''))
                    except Exception:
                        base_url = ''
                    # build absolute or relative URL depending on flag
                    if is_enabled('media_absolute_urls'):
                        base = _request_base_url(request)
                        url = f"{base}/media/images/{p.name}"
                    else:
                        url = f"/media/images/{p.name}"
                    item = {
                        'filename': p.name,
                        'url': url,
                        'size': stat.st_size,
                        'mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_mtime)),
                    }
                    # attempt to load sidecar metadata if present
                    try:
                        meta_path = p.with_suffix(p.suffix + '.json')
                        # example: img_xxx.png.json (legacy) OR img_xxx.png.json; also try .json alongside
                        if not meta_path.exists():
                            meta_path = p.with_suffix('.json')
                        if meta_path.exists():
                            try:
                                meta_text = meta_path.read_text()
                                item['metadata'] = json.loads(meta_text)
                            except Exception:
                                item['metadata'] = {'error': 'failed to read metadata'}
                    except Exception:
                        item['metadata'] = None
                    items.append(item)
        return _api_response(items)
    except Exception as exc:
        logger.exception('Failed to list media files')
        raise HTTPException(status_code=500, detail=str(exc))


@app.get('/media/images/{path:path}', include_in_schema=False)
async def serve_media_image(path: str):
    media_images = settings.media_images_dir
    candidate = media_images / path
    try:
        candidate_resolved = candidate.resolve(strict=False)
    except Exception:
        raise HTTPException(status_code=404, detail='Not Found')
    if not candidate_resolved.exists() or not candidate_resolved.is_file():
        raise HTTPException(status_code=404, detail='Not Found')
    if not str(candidate_resolved).startswith(str(media_images.resolve())):
        raise HTTPException(status_code=404, detail='Not Found')
    return FileResponse(candidate_resolved)


# Register Phase 14-16 routers (only include if the router was loaded)
if _upload_router is not None:
    app.include_router(_upload_router)
if _project_router is not None:
    app.include_router(_project_router)
if _task_router is not None:
    app.include_router(_task_router)
if _jobs_available and _job_router is not None:
    app.include_router(_job_router)


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
    # recent log buffer size (for monitoring)
    try:
        info['recent_log_lines'] = len(_recent_logs.deque)
    except Exception:
        info['recent_log_lines'] = None
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


# expose recent log lines for monitoring purposes
@app.get('/health/logs')
async def health_logs(limit: int = 100):
    """Return the most recent log messages (plain text strings).

    The query parameter `limit` controls how many lines to retrieve (max
    capacity of the ring buffer).
    """
    try:
        lines = list(_recent_logs.deque)[-limit:]
    except Exception:
        lines = []
    return JSONResponse(content={'lines': lines})


# Industry-standard hybrid memory pattern: dedicated health endpoint for
# ChromaDB so monitoring tools can verify the persistent collection is
# reachable and report how many documents are stored.
@app.get('/memory/health')
async def memory_health():
    """Return ChromaDB collection health and document count.

    Response: {"status": "ok"|"unavailable"|"error", "chroma_count": int}
    """
    try:
        mem = app.state.memory
        collection = getattr(mem, '_collection', None)
        if collection is None:
            return JSONResponse(content={"status": "unavailable", "chroma_count": 0})
        count = collection.count()
        return JSONResponse(content={"status": "ok", "chroma_count": count})
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "chroma_count": 0, "detail": str(exc)},
        )


@app.get('/api/memory/health')
async def api_memory_health():
    return await memory_health()


@app.get('/api/health')
async def api_health():
    return await health()


@app.get('/api/health/system')
async def api_health_system():
    return await health_system()


@app.get('/api/health/logs')
async def api_health_logs(limit: int = 100):
    return await health_logs(limit)


@app.get('/_health')
async def _health():
    return JSONResponse(content={"status": "ok"})


@app.get('/api/_health')
async def _health_api():
    return JSONResponse(content={"status": "ok"})


@app.get('/assets/{path:path}', include_in_schema=False)
async def serve_asset(path: str):
    candidates = [
        Path(__file__).parent / 'frontend' / 'dist' / 'assets' / path,
        Path('/vercel/output') / 'frontend' / 'dist' / 'assets' / path,
        Path('/vercel/output') / 'dist' / 'assets' / path,
        Path('/vercel/output') / 'assets' / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return FileResponse(candidate)
    raise HTTPException(status_code=404, detail='Not Found')


@app.get('/{path:path}', include_in_schema=False)
async def spa_fallback(path: str):
    # Serve static frontend files directly when they exist, then fall back
    # to the SPA entrypoint for client-side routes.
    if path and not path.startswith('api/') and not path.startswith('health') and not path.startswith('memory') and not path.startswith('media/'):
        static_candidates = [
            Path('/vercel/output') / 'frontend' / 'dist' / path,
            Path('/vercel/output') / 'dist' / path,
            Path('/vercel/output') / path,
            Path(__file__).parent / 'frontend' / 'dist' / path,
            Path(__file__).parent / path,
        ]
        for candidate in static_candidates:
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)

    # Do not override explicit API, health, or media routes handled elsewhere.
    if path.startswith('api/') or path.startswith('health') or path.startswith('memory') or path.startswith('media/'):
        raise HTTPException(status_code=404, detail='Not Found')

    candidates = [
        Path('/vercel/output') / 'frontend' / 'dist' / 'index.html',
        Path('/vercel/output') / 'dist' / 'index.html',
        Path('/vercel/output') / 'index.html',
        Path(__file__).parent / 'frontend' / 'dist' / 'index.html',
        Path(__file__).parent / 'index.html',
        Path(__file__).parent / 'frontend_index.html',
    ]
    for candidate in candidates:
        if candidate.exists():
            return HTMLResponse(content=candidate.read_text(encoding='utf-8'), status_code=200)
    raise HTTPException(status_code=404, detail='Not Found')


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8001")), reload=True)
