"""Top-level lazy FastAPI entry for Vercel.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time.
"""
from fastapi import FastAPI
import os
import json
import logging
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, FileResponse

from app import app as app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The primary FastAPI app is imported from app.py, which defines all API routes.
# We keep optional SPA fallback routes in this layer.


# Serve the static SPA index as a fallback when static build is not present in deployment
@app.get("/", include_in_schema=False)
async def serve_index():
    candidates = [
        os.path.join('frontend', 'dist', 'index.html'),
        'index.html',
        'frontend_index.html'
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return HTMLResponse(content=open(path, 'r', encoding='utf-8').read(), status_code=200)
        except Exception:
            continue
    return JSONResponse(content={"detail": "Not Found"}, status_code=404)


@app.get('/index.html', include_in_schema=False)
async def serve_index_html():
    return await serve_index()


@app.get('/api/_health')
async def api_health():
    return JSONResponse(content={"status": "ok"})


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


@app.get('/_health')
async def _health():
    return {"status": "ok"}


# Alias health endpoint for Vercel route that forwards under /api/
@app.get('/api/_health')
async def _health_api():
    return {"status": "ok"}


# Backwards-compatible health path used by some probes
@app.get('/health')
async def health_plain():
    return {"status": "ok"}


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

