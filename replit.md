# Concierge AI

An AI agent assistant with a Python FastAPI backend and a Vite+React frontend, ported to Replit's pnpm workspace stack.

## Run & Operate

- `pnpm --filter @workspace/concierge run dev` — run the frontend (port from `$PORT`)
- `uvicorn app:app --host 0.0.0.0 --port 8000` — run the Python API backend
- Start application workflow: `PORT=20721 BASE_PATH=/ pnpm --filter @workspace/concierge run dev`
- Python backend workflow: `uvicorn app:app --host 0.0.0.0 --port 8000` (from workspace root)

## Docker

Three files at workspace root: `Dockerfile`, `docker-compose.yml`, `.dockerignore`.

**Quick start (API only — no Redis, tasks run inline):**
```bash
docker build -t concierge-ai .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e GEMINI_API_KEY=... \
  concierge-ai
```
App (API + SPA) is at http://localhost:8000.

**Full stack (API + Redis broker + Celery worker):**
```bash
OPENAI_API_KEY=sk-... GEMINI_API_KEY=... docker compose up
```

**Build stages:**
1. `frontend-builder` — Node 24 + pnpm builds the React/Vite SPA (`BASE_PATH=/`)
2. `runtime` — Python 3.11-slim installs `requirements.full.txt`, copies all Python source and the built frontend into `frontend/dist/` (where `app.py`'s `_find_static_dir()` expects it)

FastAPI serves everything on port 8000 — no separate Vite dev server in Docker.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: Vite 7 + React 19 + Zustand + React Router
- Backend: Python FastAPI + uvicorn (port 8000)
- Styling: Tailwind CSS v4
- HTTP client: Axios (relative baseURL via Vite proxy)

## Where things live

- `artifacts/concierge/` — React frontend (Vite)
- `artifacts/concierge/src/` — all frontend source
- `artifacts/concierge/src/state/appStore.ts` — Zustand global store
- `artifacts/concierge/src/api/` — API service modules
- `artifacts/concierge/src/features/` — page-level components
- `artifacts/concierge/src/components/` — shared UI components
- `artifacts/concierge/vite.config.ts` — Vite config with proxy rules
- `app.py` — FastAPI main app (workspace root)
- `task_tree_store.py` — task/Redis state (workspace root)

## Architecture decisions

- Vite proxy forwards `/api`, `/media`, `/ws` → `http://localhost:8000` so frontend uses relative URLs
- Pages use `React.lazy()` with Suspense; zustand is in `optimizeDeps.include` so Vite pre-bundles it with the shared ESM React (eliminates duplicate-React / invalid-hook-call bug)
- `optimizeDeps.include: ["react", "react-dom", "axios", "zustand"]` — all bundled together to share one React instance
- `resolve.conditions: ["import", "module", "browser", "default"]` forces ESM resolution for all deps
- Redis/Celery features (task queuing, pub/sub) gracefully degrade when Redis is not running
- **Artifact routing**: `artifacts/concierge/artifact.toml` has ONE service (`web`, port 20721). The `artifacts/api-server/artifact.toml` uses path `/node-api` (NOT `/api`) so it never intercepts the Python API traffic. All `/api/*` requests flow: Replit proxy → Vite (20721) → Vite proxy → uvicorn (8000). If you ever see 502s on `/api`, check that no other artifact claims `/api` in its `paths`.
- **Python Backend workflow** (`uvicorn app:app --host 0.0.0.0 --port 8000`) runs as a standalone non-artifact workflow so it survives artifact toml changes.

## Product

Concierge AI is an agentic assistant with:
- Chat panel on the **left** on desktop (380px), page content on the right
- Live timeline/planning view with task graph visualization
- Goals, Strategy, Tasks, Workspace, Media, Guide, and Integrations pages
- Background job submission and polling
- File upload and workspace management

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Redis must be running for task queue, pub/sub timeline streaming, and job history to work. Without it, those features log errors but the app stays functional.
- The `PORT` and `BASE_PATH` env vars are required by `vite.config.ts` — it throws if either is missing.
- Always run `sed -i 's/\r//' src/**/*.ts src/**/*.tsx` after importing files from Windows to strip CRLF line endings.
- **502 on /api?** — check `artifacts/api-server/artifact.toml` paths: it must be `/node-api`, not `/api`. The Replit platform routes by the first artifact whose `paths` matches; if api-server claims `/api` it wins over Vite and hits the wrong port.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
