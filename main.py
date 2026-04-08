"""Top-level lazy FastAPI entry for Vercel.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time.
"""
from fastapi import FastAPI
import os
import json
import logging
from pathlib import Path
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, FileResponse

# SERVER_URL is used by the lightweight /health endpoint for ngrok
# tunneling and Vercel frontend checks. It defaults to the local backend
# address but can be overridden in deployment.
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8001")

from app import app as app
from fastapi.staticfiles import StaticFiles

# Do not mount SPA on "/" before API routes; mount after routes is preferred.
# The API router in app.py must take precedence for paths like /api/v1/tasks.
# We'll maintain SPA static files via explicit /spa path and fallback route.
app.mount(
    "/spa",
    StaticFiles(directory=os.path.join("frontend", "dist"), html=True),
    name="spa",
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The primary FastAPI app is imported from app.py, which defines all API routes.
# We keep optional SPA fallback routes in this layer.


# Serve the static SPA index as a fallback when static build is not present in deployment
def _spa_index_candidates() -> list[str]:
    root = Path(__file__).resolve().parent
    return [
        root / 'frontend' / 'dist' / 'index.html',
        Path(os.getcwd()) / 'frontend' / 'dist' / 'index.html',
        Path('/vercel/output/static/index.html'),
        Path('/vercel/path0/frontend/dist/index.html'),
        Path('/vercel/path0/index.html'),
    ]


def _find_spa_index() -> Path | None:
    for p in _spa_index_candidates():
        if p.exists():
            return p
    return None


@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = _find_spa_index()
    if index_path is None:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return FileResponse(str(index_path), media_type='text/html')


@app.get('/index.html', include_in_schema=False)
async def serve_index_html():
    return await serve_index()


@app.get('/api/v1/tasks', include_in_schema=False)
async def debug_tasks():
    from tasks.task_router import get_queue
    tasks = get_queue().list_tasks()
    return JSONResponse(content={
        'status': 'success',
        'data': [{'id': t.id, 'status': t.status.value, 'created_at': t.created_at} for t in tasks],
    })


@app.get('/openapi.json')
async def openapi():
    return JSONResponse(content=app.openapi())


@app.get('/assets/{path:path}', include_in_schema=False)
async def serve_asset(path: str):
    candidates = [
        os.path.join('frontend', 'dist', 'assets', path),
        os.path.join('assets', path)
    ]
    for p in candidates:
        if os.path.exists(p):
            return FileResponse(p)
    return JSONResponse(content={"detail": "Not Found"}, status_code=404)


@app.get('/{full_path:path}', include_in_schema=False)
async def serve_spa_catchall(full_path: str):
    # Fallback for SPA routing (client-side paths not defined in backend routes).
    # The real app may mount its own routes; this provides a safe fallback when
    # the static build is present under frontend/dist.
    return await serve_index()


@app.get('/spa/{path:path}', include_in_schema=False)
async def serve_spa_file(path: str):
    index_path = _find_spa_index()
    if index_path is None:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return FileResponse(str(index_path), media_type='text/html')


@app.get('/_health')
async def _health():
    return {"status": "ok", "server_url": SERVER_URL}


# Alias health endpoint for Vercel route that forwards under /api/
@app.get('/api/_health')
async def _health_api():
    return {"status": "ok", "server_url": SERVER_URL}


# Backwards-compatible health path used by some probes
@app.get('/health')
async def health_plain():
    return {"status": "ok", "server_url": SERVER_URL}


# Temporary debug endpoint to list deployed files. Remove after debugging.
@app.get('/__files')
async def _list_files():
    roots = ['.', '/vercel/output']
    files = []
    max_entries = 1000
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    try:
                        size = os.path.getsize(path)
                    except Exception:
                        size = None
                    files.append({'path': path.replace('\\', '/'), 'size': size})
                    if len(files) >= max_entries:
                        break
                if len(files) >= max_entries:
                    break
        except Exception:
            continue
        if len(files) >= max_entries:
            break
    return JSONResponse(content={'files_count': len(files), 'files': files})

