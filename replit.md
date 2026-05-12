# Concierge AI

An AI agent assistant with a Python FastAPI backend, a Vite+React web frontend, and an Expo React Native mobile app — all in a pnpm monorepo on Replit.

## Run & Operate

### Web frontend
```
PORT=20721 BASE_PATH=/ pnpm --filter @workspace/concierge run dev
```

### Python backend
```
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Mobile app (Expo)
```
pnpm --filter @workspace/concierge-mobile run dev
```

## Docker

Files at workspace root: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `requirements.prod.txt`, `.env.example`.

**Quick start (API + SPA only — no Redis, tasks run inline):**
```bash
cp .env.example .env   # fill in OPENAI_API_KEY etc.
docker compose up
```
App is at http://localhost:8000.

**Full stack (API + Redis + Celery worker):**
```bash
docker compose --profile full up
```

**One-liner without .env:**
```bash
docker build -t concierge-ai .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... concierge-ai
```

**Docker Desktop workflow (no extra setup required — buildx is built in):**
```bash
cp .env.example .env      # fill in OPENAI_API_KEY etc.
make build                # builds for your machine's native arch (auto-detected)
make up                   # start API + SPA at http://localhost:8000
make up-full              # start API + Redis + Celery worker
make logs                 # tail live container logs
make shell                # open a shell inside the running api container
```

**Push a multi-arch image (amd64 + arm64) to a registry:**
```bash
make push REGISTRY=docker.io/yourname TAG=v1.0
```
No `docker buildx create` needed — Docker Desktop's built-in builder handles both architectures.

**Build stages:**
1. `frontend-builder` — runs on `$BUILDPLATFORM` (your machine's native arch) so the Node/Vite build is never emulated via QEMU; JS/CSS output is arch-neutral.
2. `runtime` — targets `$TARGETPLATFORM`; Python 3.11-slim-bookworm, `requirements.prod.txt` (no test deps, adds gunicorn), non-root `appuser`. pip and pnpm caches are keyed per platform.

`onnxruntime` and `chromadb` both ship pre-built wheels for `linux/amd64` and `linux/arm64` — no special handling needed.

**Serving:** gunicorn + UvicornWorker — production-grade multi-process ASGI. Override with `WORKERS` env var (default 2).

FastAPI serves the SPA at `/` and the API at `/api/*` — no separate Vite server in Docker.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Web frontend: Vite 7 + React 19 + Zustand + React Router
- Mobile app: Expo (React Native) + Expo Router, Inter font, 2-tab layout
- Backend: Python FastAPI + uvicorn (port 8000)
- Styling: Tailwind CSS v4 (web), custom color tokens (mobile)
- HTTP client: Axios/fetch (relative baseURL via Vite proxy on web; `EXPO_PUBLIC_DOMAIN` on mobile)

## Where things live

- `artifacts/concierge/` — React/Vite web frontend
- `artifacts/concierge/src/` — all frontend source
- `artifacts/concierge/src/state/appStore.ts` — Zustand global store
- `artifacts/concierge/src/api/` — API service modules
- `artifacts/concierge/src/features/` — page-level components
- `artifacts/concierge/src/components/` — shared UI components
- `artifacts/concierge/vite.config.ts` — Vite config with proxy rules
- `artifacts/concierge-mobile/` — Expo React Native mobile app
- `artifacts/concierge-mobile/app/(tabs)/` — Chat and Tasks screens
- `artifacts/concierge-mobile/lib/api.ts` — typed mobile API client
- `artifacts/concierge-mobile/constants/colors.ts` — brand color tokens
- `app.py` — FastAPI main app (workspace root)
- `task_tree_store.py` — task/Redis state (workspace root)

## Architecture decisions

- Vite proxy forwards `/api`, `/media`, `/ws` → `http://localhost:8000` so web frontend uses relative URLs
- Pages use `React.lazy()` with Suspense; `react`, `react-dom`, `axios`, `zustand`, `react-router-dom` are all in `optimizeDeps.include` and `resolve.dedupe` — eliminates duplicate-React / invalid-hook-call bugs
- `resolve.conditions: ["import", "module", "browser", "default"]` forces ESM resolution for all deps
- Redis/Celery features (task queuing, pub/sub) gracefully degrade when Redis is not running
- **Artifact routing**: `artifacts/concierge/artifact.toml` has ONE service (`web`, port 20721). The `artifacts/api-server/artifact.toml` uses path `/node-api` (NOT `/api`) so it never intercepts the Python API traffic. All `/api/*` requests flow: Replit proxy → Vite (20721) → Vite proxy → uvicorn (8000). If you ever see 502s on `/api`, check that no other artifact claims `/api` in its `paths`.
- **Python Backend workflow** (`uvicorn app:app --host 0.0.0.0 --port 8000`) runs as a standalone non-artifact workflow so it survives artifact toml changes.
- **Mobile API base URL**: set via `EXPO_PUBLIC_DOMAIN` env var at startup in `app/_layout.tsx`; calls `setApiBaseUrl()` in `lib/api.ts`.

## Product

Concierge AI is an agentic assistant with:
- Chat panel on the **left** on desktop (380px), page content on the right
- Mobile-first responsive layout with hamburger nav on small screens
- Live timeline/planning view with task graph visualization
- Goals, Strategy, Tasks, Workspace, Media, Guide, and Integrations pages
- Background job submission and polling
- File upload and workspace management
- Native mobile companion app (Expo) — Chat tab + Tasks monitor tab

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Redis must be running for task queue, pub/sub timeline streaming, and job history to work. Without it, those features log errors but the app stays functional.
- The `PORT` and `BASE_PATH` env vars are required by `vite.config.ts` — it throws if either is missing.
- Always run `sed -i 's/\r//' src/**/*.ts src/**/*.tsx` after importing files from Windows to strip CRLF line endings.
- **502 on /api?** — check `artifacts/api-server/artifact.toml` paths: it must be `/node-api`, not `/api`. The Replit platform routes by the first artifact whose `paths` matches; if api-server claims `/api` it wins over Vite and hits the wrong port.
- **Mobile backend URL**: `EXPO_PUBLIC_DOMAIN` must be set for the mobile app to reach the Python API. In Replit this resolves to the dev domain automatically.
- **git push**: Use `GIT_LFS_SKIP_PUSH=1 git push ...` — git LFS tmp locks are blocked by the Replit sandbox.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
