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
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx
import hashlib
import re
from datetime import datetime

# Defer heavy/optional imports to runtime to keep module import small for
# serverless builds. Populate these in the lifespan startup.
SacredTimeline = None
AsyncConcurrencyManager = None
MemoryStore = None
get_settings = None

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

# SERVER_URL is used for ngrok/Vercel staging checks and should be overridable
# in deployment environments. Use this value anywhere the app needs its own
# public backend address for links, webhooks, or self-referential endpoints.
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8001")

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


@asynccontextmanager
async def _lifespan(application: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────
    application.state.start_time = time.time()
    application.state.conversation = []  # in-memory history; cleared on restart
    import importlib
    global is_enabled
    # late-import configuration and core components
    cfg_mod = importlib.import_module('config.settings')
    get_settings = getattr(cfg_mod, 'get_settings')
    settings = get_settings()

    chroma_path = os.getenv('CHROMA_PATH', '/app/chroma')
    try:
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception('Failed to create CHROMA_PATH directory %s', chroma_path)

    concurrency_mod = importlib.import_module('core.concurrency')
    AsyncConcurrencyManager = getattr(concurrency_mod, 'AsyncConcurrencyManager')

    memory_mod = importlib.import_module('memory.memory_store')
    MemoryStore = getattr(memory_mod, 'MemoryStore')

    orches_mod = importlib.import_module('orchestration.sacred_timeline')
    SacredTimeline = getattr(orches_mod, 'SacredTimeline')

    # feature flag helper (populate module-level `is_enabled` so route handlers
    # can call it without requiring imports)
    try:
        ff_mod = importlib.import_module('core.feature_flags')
        is_enabled = getattr(ff_mod, 'is_enabled')
    except Exception:
        is_enabled = lambda name: False

    application.state.concurrency = AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
    application.state.memory = MemoryStore(collection_name=settings.memory_collection)
    application.state.timeline = SacredTimeline(
        concurrency_manager=application.state.concurrency,
        memory_store=application.state.memory,
    )
    # start background media cleanup task
    async def _media_cleanup_loop():
        try:
            media_images = Path(__file__).parent / 'media' / 'images'
            max_age = int(os.getenv('MEDIA_MAX_AGE_SECONDS', str(60 * 60 * 24 * 7)))
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
    _include_router_from_module(application, 'workstation', 'upload_router')
    _include_router_from_module(application, 'projects', 'project_router')
    _include_router_from_module(application, 'tasks', 'task_router')

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

# create the FastAPI app with the lifespan context manager
app = FastAPI(lifespan=_lifespan, openapi_url="/openapi.json")


def _include_router_from_module(application, module_name, router_attr):
    """Include optional routers by module/attribute and avoid duplicates."""
    try:
        import importlib

        module = importlib.import_module(module_name)
        router = getattr(module, router_attr, None)
        if router is None:
            return False

        prefix = getattr(router, "prefix", None)
        if prefix:
            existing = [r.path for r in application.routes if hasattr(r, "path")]
            if any(p.startswith(prefix) or prefix.startswith(p) for p in existing):
                logger.info("Router already included: %s.%s", module_name, router_attr)
                return True

        application.include_router(router)
        logger.info("Included router at import time: %s.%s", module_name, router_attr)
        return True
    except Exception:
        logger.exception("Failed to include router %s.%s", module_name, router_attr)
        return False


# Even when lifespan callbacks are skipped in some hosting environments, make sure
# key routers are registered from module import time so API paths remain available.
_include_router_from_module(app, "workstation", "upload_router")
_include_router_from_module(app, "projects", "project_router")
_include_router_from_module(app, "tasks", "task_router")

# Serve generated media (images/audio/video) from /media
try:
    media_path = Path(__file__).parent / "media"
    try:
        media_path.mkdir(exist_ok=True)
        app.mount("/media", StaticFiles(directory=str(media_path)), name="media")
    except OSError as _err:
        import errno as _errno
        # On serverless platforms the package directory may be read-only.
        # Fall back to a writable directory from env or /tmp, then /var/task.
        if getattr(_err, 'errno', None) == _errno.EROFS or getattr(_err, 'errno', None) == 30:
            candidate_dirs = [
                os.getenv('MEDIA_DIR', ''),
                '/tmp/media',
                str(Path.cwd() / 'media'),
                '/var/task/media',
            ]
            mounted = False
            for candidate in candidate_dirs:
                if not candidate:
                    continue
                tmp_media = Path(candidate)
                try:
                    tmp_media.mkdir(parents=True, exist_ok=True)
                except Exception:
                    logger.exception("Could not create candidate media dir %s", tmp_media)
                    continue
                # quick writable check
                test_file = tmp_media / ".write_test"
                try:
                    with test_file.open("w", encoding="utf-8") as f:
                        f.write("ok")
                    try:
                        test_file.unlink()
                    except Exception:
                        pass
                except Exception:
                    logger.exception("Candidate media dir not writable: %s", tmp_media)
                    continue

                try:
                    app.mount("/media", StaticFiles(directory=str(tmp_media)), name="media")
                    media_path = tmp_media
                    logger.warning("Using fallback media dir: %s", tmp_media)
                    mounted = True
                    break
                except Exception:
                    logger.exception("Failed to mount fallback media directory %s", tmp_media)
            if not mounted:
                logger.error("Could not mount any fallback media directory")
                raise
        else:
            raise
except Exception:
    logger.exception("Failed to mount media directory for static files")

# Seed the logo into the media directory for reliable /media access.
try:
    candidate_paths = [
        Path(__file__).parent / 'frontend' / 'dist' / 'logo-optimized.svg',
        Path(__file__).parent / 'frontend' / 'public' / 'logo-optimized.svg',
        Path('/vercel/path0') / 'frontend' / 'dist' / 'logo-optimized.svg',
        Path('/vercel/path0') / 'frontend' / 'public' / 'logo-optimized.svg',
        Path('/vercel/output/static') / 'logo-optimized.svg',
    ]
    source_logo = next((p for p in candidate_paths if p.exists()), None)
    if source_logo and media_path.exists() and media_path.is_dir():
        target_logo = media_path / 'logo-optimized.svg'
        if not target_logo.exists() or source_logo.stat().st_mtime > target_logo.stat().st_mtime:
            import shutil
            shutil.copy2(str(source_logo), str(target_logo))
except Exception:
    logger.exception('Failed to seed logo into media directory')

# ----------------------------------------------------------------------
# CORS setup
# ----------------------------------------------------------------------
# The frontend commonly runs on localhost:5173 during development, so allow
# that origin (or use wildcard for convenience).  Automation tests and
# automated environments may set CORS_ALLOW_ORIGINS env var as a comma
# separated list.
from fastapi.middleware.cors import CORSMiddleware

allow_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*", "*"],
    allow_headers=["*"],
)


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
    history: Optional[List[Dict[str, Any]]] = None

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


def _session_id_from_request(request: Request) -> str:
	"""Get or create a lightweight per-user session id for media ownership tracking."""
	cookie_id = request.cookies.get('session_id')
	if cookie_id and isinstance(cookie_id, str) and cookie_id.strip():
		return cookie_id
	# generate stable random id for this session and set cookie in response path
	return str(uuid.uuid4())
def _ensure_timeline_available():
    """Raise HTTP 503 if the application's timeline component is not ready.

    Some serverless deployments may mount the app before background
    components initialize; guard endpoints that rely on `app.state.timeline`
    so they return a 503 (service temporarily unavailable) instead of
    raising an AttributeError and producing a 500.
    """
    if not hasattr(app.state, 'timeline') or app.state.timeline is None:
        raise HTTPException(status_code=503, detail='service temporarily unavailable')


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


@app.post("/api/v1/concierge/message")
async def concierge_message(payload: ConciergeMessagePayload, request: Request):
    # the Pydantic validator above guarantees we have a nonempty `message`
    msg = payload.message
    _ensure_timeline_available()
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

    # Media output is retired from message content; any media should be consumed via /api/v1/concierge/media.
    # We do not rewrite image URLs in the response content. The message content remains the same as LM output.
    data['content'] = content_val

    # append entries to conversation state (used by /conversation endpoint)
    app.state.conversation.append(user_entry)
    app.state.conversation.append(data)

    # build the API response envelope and copy provider/error info into meta
    resp = _api_response(data)
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


@app.get('/api/v1/env-check')
async def api_env_check():
    """Report runtime environment variable availability and media directory state."""
    openai_present = bool(os.getenv('OPENAI_API_KEY'))
    gemini_present = bool(os.getenv('GEMINI_API_KEY'))
    media_dir = os.getenv('MEDIA_DIR', '/tmp/media')
    media_dir_path = Path(media_dir)
    media_dir_exists = media_dir_path.exists()
    media_dir_writable = False
    try:
        media_dir_writable = media_dir_path.is_dir() and os.access(media_dir_path, os.W_OK)
    except Exception:
        media_dir_writable = False

    payload = {
        'OPENAI_API_KEY': openai_present,
        'GEMINI_API_KEY': gemini_present,
        'MEDIA_DIR': media_dir,
        'MEDIA_DIR_EXISTS': media_dir_exists,
        'MEDIA_DIR_WRITABLE': media_dir_writable,
        'HEALTHCHECK': True,
    }
    return _api_response(payload)


# timeline introspection endpoints
@app.get('/api/v1/concierge/timeline')
async def concierge_timeline():
    _ensure_timeline_available()
    plan = app.state.timeline.get_last_plan()
    return _api_response(plan or {})

@app.get('/api/v1/concierge/timeline/graph')
async def concierge_timeline_graph():
    _ensure_timeline_available()
    png = app.state.timeline.get_plan_graph_png()
    # return as a streaming response of raw PNG bytes
    return StreamingResponse(iter([png]), media_type='image/png')


@app.get('/api/v1/concierge/timeline/stream')
async def concierge_timeline_stream():
    """Server-Sent Events endpoint streaming timeline updates in real-time."""
    async def event_generator():
        _ensure_timeline_available()
        # subscribe to the timeline updates
        q = app.state.timeline.subscribe_timeline()
        try:
            while True:
                update = await q.get()
                import json as _json
                yield f"data: {_json.dumps(update)}\n\n"
        finally:
            try:
                app.state.timeline.unsubscribe_timeline(q)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type='text/event-stream')


@app.post('/api/v1/concierge/stream')
async def concierge_stream(payload: ConciergeMessagePayload):
    """Server-Sent Events endpoint — streams tokens as they are produced by the LLM.

    Each SSE event carries a JSON-encoded dict.  See
    ``SacredTimeline.stream_user_input`` for the event shapes.

    The client should open this with ``fetch`` + ``ReadableStream`` (or
    an ``EventSource`` that supports POST — most libraries do).
    """
    msg = payload.message

    _ensure_timeline_available()

    async def _event_gen():
        try:
            async for evt_json in app.state.timeline.stream_user_input(msg):
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


@app.get('/api/v1/concierge/conversation')
async def concierge_conversation():
    return _api_response(list(app.state.conversation))


@app.get('/memory/health')
async def memory_health():
    try:
        mem = app.state.memory
        if getattr(mem, '_collection', None) is not None and hasattr(mem._collection, 'count'):
            chroma_count = mem._collection.count()
        elif getattr(mem, '_client', None) is None:
            chroma_count = len(getattr(mem, '_in_memory', []))
        else:
            chroma_count = None
        return JSONResponse(content={'status': 'ok', 'chroma_count': chroma_count})
    except Exception:
        return JSONResponse(content={'status': 'error', 'chroma_count': None}, status_code=500)


@app.get('/api/v1/concierge/media')
async def concierge_media_list(request: Request):
    """Admin listing of saved media files (media/images)."""
    try:
        media_images = Path(__file__).parent / 'media' / 'images'
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
                        base = str(request.base_url).rstrip('/')
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
        session_id = _session_id_from_request(request)
        resp = JSONResponse(content=_api_response(items))
        resp.set_cookie('session_id', session_id, httponly=True, samesite='Lax', max_age=60 * 60 * 24)
        return resp
    except Exception as exc:
        logger.exception('Failed to list media files')
        raise HTTPException(status_code=500, detail=str(exc))


@app.post('/api/v1/concierge/media/cleanup')
async def concierge_media_cleanup(request: Request):
    """Delete media/images files owned by the current session."""
    session_owner = _session_id_from_request(request)
    media_images = Path(__file__).parent / 'media' / 'images'
    removed = []
    if media_images.exists():
        for p in media_images.iterdir():
            if not p.is_file() or p.suffix.lower() == '.json':
                continue
            meta_path = p.with_suffix(p.suffix + '.json')
            if not meta_path.exists():
                # fallback: adjacent .json sidecar
                meta_path = p.with_suffix('.json')
            if not meta_path.exists():
                continue
            try:
                metadata = json.loads(meta_path.read_text())
            except Exception:
                metadata = {}
            owner = metadata.get('owner')
            if owner == session_owner:
                try:
                    p.unlink()
                except Exception:
                    pass
                try:
                    if meta_path.exists():
                        meta_path.unlink()
                except Exception:
                    pass
                removed.append(p.name)
    resp = JSONResponse(content=_api_response({'removed': removed}))
    resp.set_cookie('session_id', session_owner, httponly=True, samesite='Lax', max_age=60 * 60 * 24)
    return resp


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
    if _plugin_reg is None:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'request_id': str(int(datetime.utcnow().timestamp() * 1000)),
                'data': None,
                'meta': {'confidence': None, 'priority': None, 'media': None, 'llm': {'provider': None, 'error': None}},
                'errors': {'message': 'plugin registry unavailable'},
            },
        )
    return _api_response(_plugin_reg.list_plugins())


@app.get('/api/v1/tools')
async def get_tools():
    """List all registered tools and their metadata."""
    if _list_tool_names is None or _get_tool is None:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'request_id': str(int(datetime.utcnow().timestamp() * 1000)),
                'data': None,
                'meta': {'confidence': None, 'priority': None, 'media': None, 'llm': {'provider': None, 'error': None}},
                'errors': {'message': 'tool registry unavailable'},
            },
        )
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
    if _intg_reg is None:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'request_id': str(int(datetime.utcnow().timestamp() * 1000)),
                'data': None,
                'meta': {'confidence': None, 'priority': None, 'media': None, 'llm': {'provider': None, 'error': None}},
                'errors': {'message': 'integration registry unavailable'},
            },
        )

    if not (_openai_set or _gemini_set):
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'request_id': str(int(datetime.utcnow().timestamp() * 1000)),
                'data': None,
                'meta': {'confidence': None, 'priority': None, 'media': None, 'llm': {'provider': None, 'error': None}},
                'errors': {'message': 'No AI API key configured; set OPENAI_API_KEY or GEMINI_API_KEY.'},
            },
        )

    return _api_response(_intg_reg.list_integrations())


# --- health endpoints ------------------------------------------------------
@app.get('/api/_health')
async def api_health():
    return JSONResponse(content={"status": "ok"})

@app.get('/logo-optimized.svg', include_in_schema=False)
async def logo_optimized_svg():
    candidates = [
        Path(__file__).parent / 'media' / 'logo-optimized.svg',
        Path(__file__).parent / 'frontend' / 'dist' / 'logo-optimized.svg',
        Path(__file__).parent / 'frontend' / 'public' / 'logo-optimized.svg',
        Path('/vercel/path0') / 'frontend' / 'dist' / 'logo-optimized.svg',
        Path('/vercel/path0') / 'frontend' / 'public' / 'logo-optimized.svg',
        Path('/vercel/output/static') / 'logo-optimized.svg',
    ]
    for path in candidates:
        if path.exists():
            return FileResponse(str(path), media_type='image/svg+xml')
    raise HTTPException(status_code=404, detail='Logo not found')

@app.get('/health')
async def health():
    # Lightweight health endpoint for free ngrok tunneling and Vercel frontend
    # checks. Returns the configured SERVER_URL so the tunnel target is obvious.
    return JSONResponse(content={"status": "ok", "server_url": SERVER_URL})

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
