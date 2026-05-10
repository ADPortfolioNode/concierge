# Concierge AI

An AI agent assistant with a Python FastAPI backend and a Vite+React frontend, ported to Replit's pnpm workspace stack.

## Run & Operate

- `pnpm --filter @workspace/concierge run dev` — run the frontend (port from `$PORT`)
- `uvicorn app:app --host 0.0.0.0 --port 8000` — run the Python API backend
- Start application workflow: `PORT=20721 BASE_PATH=/ pnpm --filter @workspace/concierge run dev`
- Python backend workflow: `uvicorn app:app --host 0.0.0.0 --port 8000` (from workspace root)

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
- Pages are eagerly imported (not lazy) to avoid Zustand/React duplicate instance issue with Vite's CJS interop
- `optimizeDeps.include: ["react", "react-dom", "axios"]` and `exclude: ["zustand"]` prevent the Vite pre-bundler from creating a separate CJS React copy inside Zustand
- `resolve.conditions: ["import", "module", "browser", "default"]` forces ESM resolution for all deps
- Redis/Celery features (task queuing, pub/sub) gracefully degrade when Redis is not running

## Product

Concierge AI is an agentic assistant with:
- Chat interface (left sidebar on desktop)
- Live timeline/planning view with task graph visualization
- Goals, Strategy, Tasks, Workspace, Media, Guide, and Integrations pages
- Background job submission and polling
- File upload and workspace management

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- **Never use `React.lazy()` for page routes** — Vite's CJS interop inserts `"use strict"` before the React Fast Refresh preamble in modules that transitively import CJS libs (axios, etc.), causing an "Invalid hook call" error. Use eager imports in `src/app/routes.tsx` instead.
- Redis must be running for task queue, pub/sub timeline streaming, and job history to work. Without it, those features log errors but the app stays functional.
- The `PORT` and `BASE_PATH` env vars are required by `vite.config.ts` — it throws if either is missing.
- Always run `sed -i 's/\r//' src/**/*.ts src/**/*.tsx` after importing files from Windows to strip CRLF line endings.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
