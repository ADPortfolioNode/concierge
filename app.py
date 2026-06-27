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
import threading
import uuid
from typing import Any, Optional, Deque
from pathlib import Path 
from config.settings import get_settings
import collections

# In-memory cache for capabilities endpoint
_capabilities_cache: Optional[dict[str, Any]] = None
_capabilities_cache_expiry: float = 0.0
CACHE_TTL_SECONDS = 300  # 5 minutes


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

# Silence noisy ChromaDB telemetry errors (harmless version mismatch with posthog)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY", "false")

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse, Response, HTMLResponse, FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pathlib import Path
import httpx
import redis
import hashlib
import re #
from datetime import datetime 
from task_tree_store import get_redis, get_task_tree, upsert_task_node, _find_node_in_tree #

# Defer heavy/optional imports to runtime to keep module imports small for
# serverless builds. Populate these in the lifespan startup.
SacredTimeline = None
# Lazy import for browser utility to avoid top-level overhead
_open_browser_func = None
def open_browser(url: str, delay: float = 0.0):
    global _open_browser_func
    if _open_browser_func is None:
        from core.browser import open_browser as _ob
        _open_browser_func = _ob
    _open_browser_func(url, delay=delay)

AsyncConcurrencyManager = None
MemoryStore = None

# capability layers placeholders 
load_default_plugins = None
_celery_app = None # Global Celery app instance
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

# --- service registry ------------------------------------------------------
async def update_service_registry(status: str, url: Optional[str] = None):
    """Registers or updates this service's info in the Redis registry."""
    try:
        client = get_redis()
        if not client:
            logger.warning("Service registry unavailable: Redis client not configured.")
            return

        def _do_update():
            service_key = "service:registry:concierge-backend"
            service_data = {}
            try:
                existing_data_raw = client.get(service_key)
                if existing_data_raw:
                    service_data = json.loads(existing_data_raw)
            except Exception:
                logger.warning("Could not parse existing service registry data. Starting fresh.")
                service_data = {}

            # Populate initial data if it's missing
            if "service_id" not in service_data:
                service_data.update({
                    "service_id": "concierge-backend",
                    "version": VERSION,
                    "start_time": datetime.utcnow().isoformat() + 'Z',
                    "pid": os.getpid(),
                })

            service_data["status"] = status
            service_data["last_heartbeat"] = datetime.utcnow().isoformat() + 'Z'
            
            if url:
                service_data["url"] = url
            elif "url" not in service_data:
                service_data["url"] = SERVER_URL

            client.set(service_key, json.dumps(service_data))
            
            if service_data.get("url"):
                client.sadd("cors:allowed_origins", service_data["url"].rstrip('/'))
                
            if status == "online":
                for default_origin in _get_cors_origins():
                    client.sadd("cors:allowed_origins", default_origin.rstrip('/'))

        await asyncio.to_thread(_do_update)
        logger.info(f"Updated service registry with status '{status}' and URL '{url or SERVER_URL}'.")

    except Exception:
        logger.exception("Failed to update service registry in Redis.")

_openai_set = bool(os.getenv("OPENAI_API_KEY"))
_gemini_set = bool(os.getenv("GEMINI_API_KEY"))
logger.info(f"OPENAI_API_KEY set: {_openai_set}; GEMINI_API_KEY set: {_gemini_set}")
if not _jobs_available and _jobs_import_err_msg:
    logger.warning("Distributed jobs layer unavailable: %s", _jobs_import_err_msg)

settings = get_settings()
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8000')


@asynccontextmanager
async def _lifespan(application: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────
    _total_start = time.time()
    try:
        from tqdm import tqdm
        import sys
        # Only show the progress bar in an interactive TTY. In logs (e.g., Docker),
        # the carriage returns create messy output. Fall back to plain logging.
        # Allow forcing TQDM via environment variable for Docker Compose.
        force_tqdm = os.getenv("FORCE_TQDM", "false").lower() == "true"
        if sys.stderr.isatty() or force_tqdm:
            # Corrected total and added dynamic_ncols for better rendering
            pbar = tqdm(total=12, desc="🚀 Starting Concierge", unit="step", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {desc}", dynamic_ncols=True)
        else:
            pbar = None
            logger.info("Non-TTY environment detected; using standard logs for startup.")
    except ImportError:
        pbar = None
        logger.info("Application startup sequence initiated...")

    def set_pbar_status(description: str):
        """Updates the progress bar's description without advancing it."""
        if pbar:
            pbar.set_description(f"Status: {description}")
            pbar.refresh() # Force update
        else:
            # For logging, we only want to see major steps, not every status update.
            # So this function will do nothing if there's no progress bar.
            pass

    def update_pbar(description: str):
        """Advances the progress bar by one step and updates its description."""
        if pbar:
            pbar.set_description(f"Status: {description}")
            pbar.update()
        else:
            logger.info(f"Startup: {description}...")

    async def _wait_for_url(url: str, service_name: str, timeout: int = 60) -> bool:
        """Polls a URL until it gets a 2xx response or times out."""
        set_pbar_status(f"Connecting to {service_name}")
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    # Use a short timeout for each individual request
                    response = await client.get(url, timeout=2)
                    if 200 <= response.status_code < 300:
                        set_pbar_status(f"Connection to {service_name} successful.")
                        logger.info(f"{service_name} is ready at {url}.")
                        return True
                except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout):
                    set_pbar_status(f"Connecting to {service_name} (retrying)...")
                    # These are expected if the service isn't up yet
                    pass
                except Exception:
                    logger.exception(f"Unexpected error while waiting for {service_name}")
                await asyncio.sleep(2)
        set_pbar_status(f"Timed out connecting to {service_name}.")
        logger.warning(f"Timed out waiting for {service_name} to be ready at {url}.")
        return False

    application.state.start_time = time.time()
    application.state.startup_complete = False # Set initial status
    application.state.conversation = []  # in-memory history; cleared on restart
    import importlib
    global is_enabled
    global settings, AsyncConcurrencyManager, MemoryStore, SacredTimeline
    global _celery_app, load_default_plugins, _plugin_reg, load_default_integrations, _intg_reg
    global _list_tool_names, _get_tool, _register_tool, observability_setup, MEDIA_SAVED, REQUEST_COUNTER
    global _upload_router, _project_router, _task_router, _get_task_queue, _register_task_handlers
    global _job_router, _jobs_available, _jobs_import_err_msg
    # late-import configuration and core components, advancing progress bar at each major step
    update_pbar("Importing core modules")
    _step_t0 = time.time()
    cfg_mod = importlib.import_module('config.settings')
    settings = cfg_mod.get_settings()

    concurrency_mod = importlib.import_module('core.concurrency')
    AsyncConcurrencyManager = getattr(concurrency_mod, 'AsyncConcurrencyManager')

    memory_mod = importlib.import_module('memory.memory_store')
    MemoryStore = getattr(memory_mod, 'MemoryStore')

    try:
        orches_mod = importlib.import_module('orchestration.sacred_timeline')
        SacredTimeline = getattr(orches_mod, 'SacredTimeline')
    except Exception:
        logger.exception("Isolated startup issue: Failed to import orchestration.sacred_timeline")
        SacredTimeline = None
    logger.info(f"Core modules imported in {time.time() - _step_t0:.3f}s.")

    # NEW: Wait for Redis (fast-fail for pure local dev without external Redis)
    update_pbar("Connecting to Redis")
    _redis_ready = False
    _redis_start_time = time.time()
    _redis_timeout = min(getattr(settings, "redis_init_timeout", 5), 12)
    # Quick exit if Redis URL not pointing at a real external service
    redis_url = os.getenv("REDIS_URL", "") or os.getenv("CELERY_BROKER_URL", "")
    if not redis_url or "localhost" in redis_url or "127.0.0.1" in redis_url:
        # In local dev without a running redis container we skip fast
        logger.info("Redis not configured or localhost only — skipping wait for fast local startup.")
        _redis_ready = True
    else:
        while time.time() - _redis_start_time < _redis_timeout:
            try:
                r = get_redis()
                if r is None:
                    _redis_ready = True
                    break
                is_ready = await asyncio.wait_for(asyncio.to_thread(r.ping), timeout=1.5)
                if is_ready:
                    _redis_ready = True
                    break
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
    if not _redis_ready:
        logger.warning("Continuing without Redis (some distributed features disabled).")

    # NEW: Wait for Vector DB
    # Safely get vector_db, providing a default if the attribute is missing from settings.
    # This handles cases where config.settings might not have 'vector_db' defined.
    configured_vector_db = getattr(settings, "vector_db", "chroma")
    _vector_db_url = ""
    _vector_db_name = ""
    if configured_vector_db == "chroma":
        _vector_db_name = "ChromaDB"
        _vector_db_url = f"http://{getattr(settings, 'chroma_host', 'localhost')}:{getattr(settings, 'chroma_port', 8000)}/api/v2/heartbeat"
    elif configured_vector_db == "qdrant":
        _vector_db_name = "Qdrant"
        _vector_db_url = f"http://{getattr(settings, 'qdrant_host', 'localhost')}:{getattr(settings, 'qdrant_port', 6333)}/readyz"
    
    _vdb_timeout = min(getattr(settings, 'vector_db_init_timeout', 8), 15)
    chroma_host = getattr(settings, 'chroma_host', 'localhost')
    q_host = getattr(settings, 'qdrant_host', 'localhost')
    if _vector_db_url and not (chroma_host in ('localhost','127.0.0.1') or q_host in ('localhost','127.0.0.1')):
        update_pbar(f"Connecting to {_vector_db_name}")
        await _wait_for_url(_vector_db_url, _vector_db_name, timeout=_vdb_timeout)
    else:
        logger.info("Vector DB on localhost or not configured — skipping external wait for fast startup.")
        update_pbar("Vector DB (local/in-memory mode)")

    # Initialize Celery app and pass the configurable timeout
    update_pbar("Initializing task engine (Celery)")
    try:
        celery_mod = importlib.import_module('tasks.celery_app')
        _celery_app = getattr(celery_mod, 'celery_app')
        # Import tasks to register them with Celery
        importlib.import_module('tasks.agent_tasks')
        importlib.import_module('tasks.step_assistant_tasks')
    except Exception:
        logger.exception("Isolated startup issue: Failed to load Celery app or tasks")
    # optional LLM wrapper for memory embedding support
    llm_tool = None
    try:
        llm_mod = importlib.import_module('tools.llm_tool')
        llm_cls = getattr(llm_mod, 'LLMTool')
        llm_tool = llm_cls()
    except Exception:
        llm_tool = None
    logger.info(f"Celery and LLM tools initialized in {time.time() - _step_t0:.3f}s.")

    # Initialize vector memory store, which may involve network calls.
    update_pbar("Initializing vector memory store")
    _step_t0 = time.time()
    application.state.memory = MemoryStore(collection_name=getattr(settings, 'memory_collection', 'concierge'), llm_tool=llm_tool)
    # Asynchronously initialize the vector DB client and collection
    # This handles retries and prevents blocking the main thread, using the configurable timeout.
    await application.state.memory.async_init(
        timeout=getattr(settings, 'vector_db_init_timeout', 30), 
        retry_interval=2,
        progress_callback=set_pbar_status
    )

    # feature flag helper (populate module-level `is_enabled` so route handlers can call it without requiring imports)
    logger.info(f"Vector memory initialized in {time.time() - _step_t0:.3f}s.")

    update_pbar("Initializing orchestrator (Sacred Timeline)...")
    _step_t0 = time.time()
    try:
        ff_mod = importlib.import_module('core.feature_flags')
        is_enabled = getattr(ff_mod, 'is_enabled')
    except Exception:
        is_enabled = lambda name: False
    
    if SacredTimeline:
        application.state.timeline = SacredTimeline(
            memory_store=application.state.memory,
        )
    else:
        application.state.timeline = None
    logger.info(f"Application state (timeline) initialized in {time.time() - _step_t0:.3f}s.")

    # start background media cleanup task
    update_pbar("Configuring background services")
    _step_t0 = time.time()
    async def _media_cleanup_loop():
        try:
            media_images = getattr(settings, "media_images_dir", Path("/tmp/media/images"))
            max_age = getattr(settings, "media_max_age_seconds", 86400)
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
    logger.info(f"Background tasks & observability configured in {time.time() - _step_t0:.3f}s.")

    # Register built-in tools
    update_pbar("Registering tools")
    _step_t0 = time.time()
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
        logger.warning("Could not register built-in tools.")
        pass
    logger.info(f"Built-in tools registered in {time.time() - _step_t0:.3f}s.")

    # Load capability layers (plugins/integrations)
    update_pbar("Loading capabilities")
    _step_t0 = time.time()
    try:
        pl_mod = importlib.import_module('plugins.plugin_loader')
        load_default_plugins = getattr(pl_mod, 'load_default_plugins')
        pr_mod = importlib.import_module('plugins.plugin_registry')
        _plugin_reg = pr_mod
        if load_default_plugins:
            load_default_plugins()
    except Exception:
        logger.exception('Failed to load plugins (continuing)')
        _plugin_reg = None

    try:
        il_mod = importlib.import_module('integrations.integration_loader')
        load_default_integrations = getattr(il_mod, 'load_default_integrations')
        ir_mod = importlib.import_module('integrations.integration_registry')
        _intg_reg = ir_mod
        if load_default_integrations:
            load_default_integrations()
    except Exception:
        logger.exception('Failed to load integrations (continuing)')
        _intg_reg = None
    logger.info(f"Capabilities & integrations loaded in {time.time() - _step_t0:.3f}s.")

    # Wire file-agent handlers and start the background task worker (optional)
    update_pbar("Connecting to task broker")
    _step_t0 = time.time()
    try:
        tw_mod = importlib.import_module('tasks.task_worker')
        _register_task_handlers = getattr(tw_mod, 'register_default_handlers') # type: ignore
        tq_mod = importlib.import_module('tasks')
        _get_task_queue = getattr(tq_mod, 'get_queue')
        _register_task_handlers()
        # Use a configurable, more generous timeout for the task worker connection
        # to improve startup stability on slow networks or busy systems.
        _task_worker_timeout = getattr(settings, "task_worker_init_timeout", 30)
        await asyncio.wait_for(_get_task_queue().start_worker(), timeout=_task_worker_timeout)
        set_pbar_status("Task broker connection successful.")
        logger.info(f"Task worker connection established in {time.time() - _step_t0:.3f}s.")
    except asyncio.TimeoutError:
        set_pbar_status("Timed out connecting to task broker.")
        logger.warning("Timed out connecting to task broker. Worker will be unavailable.")
    except Exception:
        set_pbar_status("Task broker connection failed.")
        logger.exception('Task worker not available or failed to start (continuing)')
    

    # Register routers from features like workstation/projects/tasks if available
    update_pbar("Registering feature routers and API endpoints...")
    _step_t0 = time.time()
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
    logger.info(f"Feature routers registered in {time.time() - _step_t0:.3f}s.")

    update_pbar("Announcing service online")
    try:
        # Use a configurable, more generous timeout for the service registry connection.
        _registry_timeout = getattr(settings, "service_registry_init_timeout", 10)
        await asyncio.wait_for(
            update_service_registry(status="online"),
            timeout=_registry_timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Timed out connecting to service registry (Redis). Skipping.")
    except Exception:
        logger.exception("Failed to announce service online status during startup.")

    set_pbar_status("Redirecting to dashboard...")
    if os.getenv("AUTO_OPEN_BROWSER", "false").lower() == "true":
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        open_browser(frontend_url, delay=1.0)

    if pbar:
        pbar.close()
        # Final startup message after progress bar
        logger.info(f"🚀 Concierge startup complete in {time.time() - _total_start:.3f}s total.")
    else:
        logger.info(f"Application startup complete in {time.time() - _total_start:.3f}s total.")

    # Signal that the application has completed its startup sequence.
    application.state.startup_complete = True
    logger.info("Application is now ready to accept connections.")

    # Load desktop application if available
    try:
        desktop_mod = importlib.import_module('desktop')
        start_desktop = getattr(desktop_mod, 'start', None)
        if callable(start_desktop):
            logger.info("Starting desktop application...")
            threading.Thread(target=start_desktop, daemon=True).start()
    except ImportError:
        pass
    except Exception:
        logger.exception("Error occurred while loading desktop application")

    yield
    # ── shutdown ─────────────────────────────────────────────────────────
    application.state.startup_complete = False
    # Unregister from service registry
    try:
        await asyncio.wait_for(update_service_registry(status="offline"), timeout=2.0)
        logger.info("Service status updated to 'offline' in the registry.")
    except Exception:
        logger.exception("Failed to update service registry on shutdown.")

    # Gracefully shutdown background tasks
    if hasattr(application.state, 'media_cleanup_task'):
        application.state.media_cleanup_task.cancel()
    if _get_task_queue and hasattr(_get_task_queue(), 'is_running') and _get_task_queue().is_running():
        try:
            await _get_task_queue().stop_worker()
            logger.info("Background task worker stopped.")
        except Exception:
            logger.exception("Error stopping background task worker.")

app = FastAPI(lifespan=_lifespan)

from fastapi.middleware.cors import CORSMiddleware

# CORS configuration is driven by a single source: CORS_ALLOW_ORIGINS.
# If unset, we fall back to the legacy allowed origins used by local dev
# and production deployments.

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:5176", "http://127.0.0.1:5176",
    "http://localhost:5177", "http://127.0.0.1:5177",
    "http://localhost:5178", "http://127.0.0.1:5178",
    "http://localhost:5179", "http://127.0.0.1:5179",
    "http://localhost:8000", # Add backend's own port for Swagger UI
    "http://127.0.0.1:8000", # Add backend's own port for Swagger UI
    "http://localhost:8001", # Docker-compose host port for backend
    "http://127.0.0.1:8001", # Docker-compose host port for backend
    "https://deoismconcierge.vercel.app",
    "https://deoismconcierge-adportfolionodes-projects.vercel.app",
]

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
    """Auto-expands localhost/127.0.0.1 aliases for any http origin."""
    expanded: list[str] = []
    seen: set[str] = set()
    for origin in origins:
        origin = origin.rstrip('/')
        if origin in seen:
            continue
        seen.add(origin)
        expanded.append(origin)
        # Auto-add localhost/127.0.0.1 aliases for any http origin
        if origin.startswith("http://localhost"):
            alias = origin.replace("http://localhost", "http://127.0.0.1", 1)
            if alias not in seen:
                seen.add(alias)
                expanded.append(alias)
        elif origin.startswith("http://127.0.0.1"):
            alias = origin.replace("http://127.0.0.1", "http://localhost", 1)
            if alias not in seen:
                seen.add(alias)
                expanded.append(alias)
    return expanded


def _get_cors_origins() -> list[str]:
    env_origins = _parse_cors_allow_origins(os.getenv("CORS_ALLOW_ORIGINS"))
    origins = env_origins if env_origins else _DEFAULT_CORS_ORIGINS
    return _expand_cors_origin_aliases(origins)


cors_origins = _get_cors_origins()

_dynamic_cors_cache: set[str] = set()
_dynamic_cors_last_sync: float = 0.0

async def _refresh_cors_cache():
    try:
        client = get_redis()
        if not client:
            return
            
        def _fetch():
            return client.smembers("cors:allowed_origins")
            
        dynamic_origins = await asyncio.to_thread(_fetch)
        if dynamic_origins:
            global _dynamic_cors_cache
            new_cache = set()
            decoded_origins = [o.decode('utf-8') if isinstance(o, bytes) else str(o) for o in dynamic_origins]
            # Expand aliases for all dynamically fetched origins
            for origin in decoded_origins:
                origin = origin.rstrip('/')
                if origin in new_cache:
                    continue
                new_cache.add(origin)
                if origin.startswith("http://localhost"):
                    alias = origin.replace("http://localhost", "http://127.0.0.1", 1)
                    new_cache.add(alias)
                elif origin.startswith("http://127.0.0.1"):
                    alias = origin.replace("http://127.0.0.1", "http://localhost", 1)
                    new_cache.add(alias)
            _dynamic_cors_cache = new_cache
    except Exception as e:
        logger.debug(f"Failed to sync dynamic CORS origins from registry: {e}")

class DynamicCORSMiddleware(CORSMiddleware):
    """Industry-standard unified registry CORS middleware.
    Validates against static rules first, then queries the unified Redis registry
    to allow distributed servers to dynamically register valid origins site-wide."""
    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        
        global _dynamic_cors_cache, _dynamic_cors_last_sync
        now = time.time()
        if now - _dynamic_cors_last_sync > 30:  # 30-second TTL for registry sync
            _dynamic_cors_last_sync = now
            try:
                # Spawn a background task to refresh the cache asynchronously.
                # This prevents blocking the main event loop during health checks or normal routing.
                loop = asyncio.get_running_loop()
                loop.create_task(_refresh_cors_cache())
            except Exception:
                pass

        return origin in _dynamic_cors_cache

# Serve generated media (images/audio/video) from /media (fallback to /tmp for serverless)
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

# CORS middleware MUST be added after @app.middleware so it is the outermost layer.
# This prevents other middlewares from intercepting errors and dropping CORS headers.
app.add_middleware(
    DynamicCORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False if "*" in cors_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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


class ServiceUrlPayload(BaseModel):
    url: str


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


# startup logic moved to _lifespan context manager above


# versioned endpoints are used by the frontend; we keep the old
# `/ask` path as an unversioned alias for compatibility but wrap all
# responses in our standard JSON envelope as well.  This makes it easier
# to relocate the logic under `/api/v1` later if desired. Legacy aliases
# have been removed to simplify the API surface.


@app.post('/api/v1/concierge/message')
async def concierge_message(payload: ConciergeMessagePayload, request: Request):
    return await _handle_chat_message(payload, request)


async def _handle_chat_message(payload: ConciergeMessagePayload, request: Request):
    # the Pydantic validator above guarantees we have a nonempty `message`
    msg = payload.message
    _ensure_timeline_available()
    thread_id = str(uuid.uuid4())
    result = await app.state.timeline.handle_user_input(msg, thread_id=thread_id)

    # If the timeline dispatched a background task, it returns a "processing" status.
    if isinstance(result, dict) and result.get('status') == 'processing':
        data = {
            'id': str(int(time.time() * 1000)),
            'role': 'assistant',
            'content': "OK, I've started working on that. You can follow the progress in real-time.",
            'meta': {'raw': result},
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }
        resp = _api_response(data)
        resp['thread_id'] = result.get('thread_id')
        resp['meta']['llm'] = {'provider': 'celery', 'error': None}
        return resp

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

    # append entries to conversation state (used by /conversation endpoint)
    app.state.conversation.append(user_entry)
    app.state.conversation.append(data)

    # build the API response envelope and copy provider/error info into meta
    resp = _api_response(data)
    resp['thread_id'] = thread_id
    # LLM metadata will be updated by the Celery tasks
    resp['meta']['llm'] = {'provider': 'celery', 'error': None}
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
        from task_tree_store import get_redis
        client = get_redis()
        if not client:
            logger.warning("Cannot list tasks, Redis is not available.")
            return _api_response([])
        task_keys = list(client.scan_iter(match='task_tree:*', count=100))
        tasks = []
        for key in await asyncio.to_thread(client.scan_iter, match='task_tree:*', count=100):
            thread_id = key.split(':', 1)[1] if ':' in key else key
            task_tree = get_task_tree(thread_id)
            if not task_tree: # type: ignore
                continue
            metadata = task_tree.get('metadata') or {}
            tasks.append({
                'id': thread_id,
                'type': metadata.get('task_type') or task_tree.get('task_name') or thread_id,
                'status': task_tree.get('status') or task_tree.get('state') or 'unknown',
                'created_at': None if metadata.get('start_time') is None else datetime.fromtimestamp(float(metadata.get('start_time'))).isoformat(),
            })
        tasks.sort(key=lambda item: item.get('created_at') or '', reverse=True) # type: ignore
        return _api_response(tasks)
    except Exception:
        logger.exception('Failed to fetch task list')
        return _api_response({'error': 'task list unavailable'}, status='error')

@app.post('/api/v1/tasks/{task_id}/kill')
async def kill_task(task_id: str):
    """Endpoint to kill a running Celery task."""
    if _celery_app is None:
        raise HTTPException(status_code=503, detail="Celery app not initialized.")

    try:
        # Revoke the task, terminating it immediately
        await asyncio.to_thread(_celery_app.control.revoke, task_id, terminate=True, signal='SIGKILL')
        # Update the task status in the task tree
        # Note: task_id is used as thread_id here if it's a root task, otherwise it's the actual task_id
        # A more robust solution might involve finding the thread_id associated with the task_id first.
        upsert_task_node(thread_id=task_id, task_id=task_id, parent_id=None, status="KILLED", result="Task killed by user.")
        logger.info(f"Task {task_id} sent SIGKILL and marked as KILLED.")
        return _api_response({"status": "success", "message": f"Task {task_id} kill signal sent."})
    except Exception as e:
        logger.exception(f"Failed to kill task {task_id}")
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": f"Failed to send kill signal to task {task_id}: {e!s}"
        })


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
async def concierge_timeline_stream(request: Request):
    """Server-Sent Events endpoint streaming timeline updates in real-time.

    Each event is a structured delta object and may include visual graph hints
    for the frontend visualizer: node_add, node_update, edge_add, task_update,
    and plan metadata.
    This endpoint now streams task tree updates from Redis Pub/Sub.
    """
    thread_id = request.query_params.get("thread_id")
    if not thread_id:
        return Response("thread_id query parameter is required.", status_code=400, media_type="text/plain")

    from task_tree_store import get_task_update_pubsub
    
    async def event_generator():
        pubsub = None
        try:
            pubsub = get_task_update_pubsub(thread_id)
            if pubsub is None:
                logger.warning(f"SSE stream for thread {thread_id} disabled: Redis is not available.")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Real-time updates are unavailable because the connection to the streaming server could not be made.'})}\n\n"
                return
            logger.info(f"SSE stream opened for thread_id: {thread_id}")
            while True:
                if await request.is_disconnected():
                    logger.info(f"SSE client for thread_id {thread_id} disconnected.")
                    break
                # Use asyncio.to_thread to run the blocking get_message call
                message = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get('data'):
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0.1)  # Yield control to the event loop
        finally:
            if pubsub:
                pubsub.close() # pubsub.unsubscribe() is called by pubsub.close()
                logger.info(f"SSE resources cleaned up for thread_id: {thread_id}")

    return StreamingResponse(event_generator(), media_type='text/event-stream')

@app.websocket('/api/v1/concierge/timeline/ws')
async def concierge_timeline_websocket(websocket: WebSocket):
    await websocket.accept()
    thread_id = websocket.query_params.get("thread_id")
    if not thread_id:
        await websocket.close(code=1008, reason="thread_id is required")
        return

    from task_tree_store import get_task_update_pubsub
    
    pubsub = get_task_update_pubsub(thread_id)
    if pubsub is None:
        logger.warning(f"WebSocket for thread {thread_id} disabled: Redis is not available.")
        try:
            await websocket.send_text(json.dumps({'type': 'error', 'message': 'Real-time updates are unavailable because the connection to the streaming server could not be made.'}))
        except Exception:
            pass # Client might have already disconnected
        await websocket.close(code=1011, reason="Real-time updates unavailable.")
        return
    try:
        while True:
            await asyncio.sleep(0.1)
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message['data']:
                await websocket.send_text(message['data'])
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for thread_id: {thread_id}")
        pass
    except Exception:
        logger.exception('Timeline websocket error')
    finally:
        try:
            if pubsub:
                pubsub.unsubscribe()
                pubsub.close()
        except Exception:
            pass


@app.get('/api/v1/concierge/threads/{thread_id}/nodes/{node_id}/memories')
async def concierge_node_memories(thread_id: str, node_id: str, top_k: int = 8):
    """Return memory snippets related to a thread node for visualizer side panels."""
    # from task_tree_store import get_task_tree, _find_node_in_tree #
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
    if not _plugin_reg:
        return _api_response([])
    return _api_response(_plugin_reg.list_plugins())


@app.get('/api/v1/tools')
async def get_tools():
    """List all registered tools and their metadata."""
    if not _list_tool_names or not _get_tool:
        return _api_response([])
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
    if not _intg_reg:
        return _api_response([])
    return _api_response(_intg_reg.list_integrations())


def _serialize_capability_list(raw_items: list[dict], default_type: str) -> list[dict]:
    """Serializes a list of capabilities into a consistent format for the API."""
    processed = []
    for item in raw_items:
        processed.append({
            "name": item.get("name"),
            "description": item.get("description", ""),
            "type": item.get("type", default_type),
            "version": item.get("version"),
            "service": item.get("service"),
            "enabled": item.get("enabled", True),
        })
    return processed

@app.get('/api/v1/capabilities')
async def get_all_capabilities(request: Request):
    """
    List all registered capabilities (plugins, tools, integrations) in a single call for efficiency.
    This endpoint is cached for 5 minutes to improve performance.
    """
    global _capabilities_cache, _capabilities_cache_expiry

    force_refresh = request.query_params.get('force', 'false').lower() == 'true'

    # Return cached response if it's still valid
    if not force_refresh and _capabilities_cache is not None and time.time() < _capabilities_cache_expiry:
        logger.info("Serving capabilities from cache.")
        return _api_response(_capabilities_cache)

    log_reason = "force refresh requested" if force_refresh else "cache stale or empty"
    logger.info(f"Generating new capabilities response: {log_reason}.")
    all_capabilities = {}

    # --- Tools ---
    try:
        if not _list_tool_names or not _get_tool:
            all_capabilities['tools'] = []
        else:
            names = _list_tool_names()
            serialized_tools = []
            for name in names:
                tool = _get_tool(name)
                # Enrich with all fields the frontend expects
                serialized_tools.append({
                    "name": name,
                    "description": getattr(tool, "description", ""),
                    "type": "tool",
                    "version": getattr(tool, "version", None),
                    "service": getattr(tool, "service", None),
                    "enabled": getattr(tool, "enabled", True),
                })
            all_capabilities['tools'] = serialized_tools
    except Exception:
        logger.exception("Failed to get tools for /api/v1/capabilities")
        all_capabilities['tools'] = []

    # --- Plugins ---
    try:
        if not _plugin_reg:
            all_capabilities['plugins'] = []
        else:
            all_capabilities['plugins'] = _serialize_capability_list(
                _plugin_reg.list_plugins(), "plugin"
            )
    except Exception:
        logger.exception("Failed to get plugins for /api/v1/capabilities")
        all_capabilities['plugins'] = []

    # --- Integrations ---
    try:
        if not _intg_reg:
            all_capabilities['integrations'] = []
        else:
            all_capabilities['integrations'] = _serialize_capability_list(
                _intg_reg.list_integrations(), "integration"
            )
    except Exception:
        logger.exception("Failed to get integrations for /api/v1/capabilities")
        all_capabilities['integrations'] = []

    # Store in cache before returning
    _capabilities_cache = all_capabilities
    _capabilities_cache_expiry = time.time() + CACHE_TTL_SECONDS
    logger.info(f"Capabilities cache updated. Next expiry in {CACHE_TTL_SECONDS} seconds.")

    return _api_response(all_capabilities)


# --- Service Registry Endpoints ---------------------------------------------

@app.post('/api/v1/server/registry/update-url')
async def update_server_url(payload: ServiceUrlPayload):
    """Updates the public URL for this service in the registry."""
    await update_service_registry(status="online", url=payload.url)
    return _api_response({"status": "success", "message": f"Service URL updated to {payload.url}"})


@app.get('/api/v1/server/registry/status')
async def get_server_registry_status():
    """Reads and returns the current service registration from Redis."""
    try:
        client = get_redis()
        if not client:
            raise HTTPException(status_code=503, detail="Service registry unavailable: Redis client not configured.")

        service_key = "service:registry:concierge-backend"
        service_data_raw = await asyncio.to_thread(client.get, service_key)

        if not service_data_raw:
            raise HTTPException(status_code=404, detail="Service not found in registry.")

        service_data = json.loads(service_data_raw)
        return _api_response(service_data)
    except Exception as e:
        logger.exception("Failed to read from service registry.")
        # Return a proper API response envelope for errors
        resp = _api_response(None, status='error')
        resp['errors'] = {'message': f"Failed to read from registry: {str(e)}"}
        return JSONResponse(status_code=500, content=resp)


# --- health endpoints ------------------------------------------------------
def _get_readiness_status() -> tuple[str, list[str]]:
    """Checks if core components are initialized and returns status and messages."""
    messages = []
    if getattr(app.state, 'startup_complete', False):
        status = "ok"
    else:
        status = "not ready"
        messages.append("Application startup is still in progress.")
    return status, messages

@app.get('/health')
async def health():
    """Return 200 OK if the application's core components are initialized.
    This endpoint is now an alias for /health/ready.
    """
    status, messages = _get_readiness_status()
    # The original /health endpoint did not return 503, just a message.
    return JSONResponse(content={"status": status, "version": VERSION, "messages": messages})

@app.get('/health/ready')
async def health_ready():
    """Return 200 OK if the application's core components are initialized."""
    status, messages = _get_readiness_status()
    if status == "ok":
        return JSONResponse(content={"status": "ok", "version": VERSION})
    else:
        return JSONResponse(status_code=503, content={"status": status, "version": VERSION, "messages": messages})

@app.get('/api/health/ready')
async def health_ready_aliased():
    """Alias for /health/ready to support clients that may incorrectly prefix with /api."""
    return await health_ready()


@app.get('/api/health')
async def health_aliased():
    """Direct /api/health alias for frontend startup checks (maps to /health)."""
    return await health()


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
    # Celery worker health
    try:
        if _celery_app:
            # Ping workers. This returns a list of replies, one for each worker that replied.
            # If the list is not empty, at least one worker is alive.
            # Use a short timeout to avoid blocking the health check for too long.
            replies = _celery_app.control.ping(timeout=1.0)
            if replies:
                info['celery_worker'] = 'ok'
                info['celery_active_workers'] = len(replies)
            else:
                info['celery_worker'] = 'unavailable'
                info['celery_active_workers'] = 0
        else:
            info['celery_worker'] = 'not configured'
    except Exception:
        # This can happen if the broker is down.
        logger.debug("Celery health check failed", exc_info=True)
        info['celery_worker'] = 'error'
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


@app.get('/_health')
async def _health():
    return JSONResponse(content={"status": "ok"})


@app.get('/api/_health')
async def _health_api():
    return JSONResponse(content={"status": "ok"})


# --- SPA/Static Files Serving -----------------------------------------------
# This logic replaces the manual /assets and /{path:path} fallbacks for better
# consistency and robustness, using FastAPI's built-in StaticFiles.

def _find_static_dir() -> Optional[Path]:
    """Find the directory containing the built frontend assets."""
    # Local development path from project root
    local_path = Path(__file__).parent / 'frontend' / 'dist'
    if local_path.exists() and (local_path / 'index.html').exists():
        logger.info(f"Found static files for SPA at: {local_path}")
        return local_path

    # Vercel deployment paths
    vercel_paths = [
        Path('/vercel/output') / 'frontend' / 'dist',
        Path('/vercel/output') / 'dist',
        Path('/vercel/output'),
    ]
    for path in vercel_paths:
        if path.exists() and (path / 'index.html').exists():
            logger.info(f"Found static files for SPA at: {path} (Vercel)")
            return path

    logger.warning("Built frontend directory not found. SPA serving will be disabled.")
    return None

STATIC_DIR = _find_static_dir()

if STATIC_DIR:
    # This single mount replaces both `serve_asset` and `spa_fallback`.
    # It serves static files and provides a fallback to index.html for client-side routing.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")


if __name__ == "__main__":
    import uvicorn
    import sys

    # Add a command-line argument to control browser opening when running app.py directly.
    # This is separate from the `--no-browser-open` flag in `start.sh`.
    # Usage: python app.py --open-browser [optional_url]
    if "--open-browser" in sys.argv:
        idx = sys.argv.index("--open-browser")
        url = "http://localhost:5173"
        # Check if a URL was provided after the flag
        if len(sys.argv) > idx + 1 and sys.argv[idx+1].startswith("http"):
            url = sys.argv.pop(idx+1)
        
        # Set the environment variable that the lifespan startup function checks.
        os.environ["AUTO_OPEN_BROWSER"] = "true"
        os.environ["FRONTEND_URL"] = url
        sys.argv.pop(idx)
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
