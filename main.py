"""Top-level lazy FastAPI entry for Vercel.

Defines a minimal `app` to satisfy Vercel's detection. The real
application is imported and mounted during startup to avoid heavy
imports at build-time.
"""
from fastapi import FastAPI
import os
import json
from fastapi.responses import JSONResponse

app = FastAPI()


@app.on_event("startup")
async def _mount_real_app():
    try:
        import importlib
        real = importlib.import_module('app')
        real_app = getattr(real, 'app', None)
        if real_app is not None:
            app.mount('/_app', real_app)
    except Exception:
        return


@app.get('/_health')
async def _health():
    return {"status": "ok"}


# Alias health endpoint for Vercel route that forwards under /api/
@app.get('/api/_health')
async def _health_api():
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

