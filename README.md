# Concierge AI

An agentic AI assistant with a Python FastAPI backend, a Vite + React web frontend, and an Expo React Native mobile app — all living in a single pnpm monorepo.

---

## Table of contents

- [Stack](#stack)
- [Project layout](#project-layout)
- [Running locally](#running-locally)
- [Docker](#docker)
- [Environment variables](#environment-variables)
- [Architecture notes](#architecture-notes)
- [Mobile app](#mobile-app)

---

## Stack

| Layer | Technology |
|-------|-----------|
| Monorepo | pnpm workspaces |
| Runtime | Node.js 24, Python 3.11 |
| Web frontend | Vite 7 + React 19 + Zustand + React Router |
| Mobile app | Expo (React Native) + Expo Router |
| Backend | FastAPI + uvicorn (port 8000) |
| Styling | Tailwind CSS v4 (web), custom tokens (mobile) |
| Task queue | Celery + Redis (optional — degrades gracefully) |
| AI | OpenAI, Gemini |

---

## Project layout

```
/
├── app.py                    # FastAPI entry point
├── main.py                   # uvicorn runner
├── task_tree_store.py        # task state + Redis pub/sub
├── task_agent.py             # agentic task executor
├── agents/                   # agent modules
├── api/                      # FastAPI routers
├── core/                     # shared backend utilities
├── jobs/                     # Celery task definitions
├── requirements.full.txt     # all Python deps
├── Dockerfile                # multi-stage build (web SPA + API)
├── docker-compose.yml        # API + Redis + Celery worker
│
├── artifacts/
│   ├── concierge/            # React/Vite web frontend (port 20721 dev)
│   │   ├── src/
│   │   │   ├── api/          # API service modules
│   │   │   ├── components/   # shared UI components
│   │   │   ├── features/     # page-level components
│   │   │   └── state/        # Zustand global store
│   │   └── vite.config.ts    # Vite config + proxy rules
│   │
│   └── concierge-mobile/     # Expo React Native mobile app
│       ├── app/              # Expo Router screens
│       │   └── (tabs)/       # Chat + Tasks tabs
│       ├── lib/api.ts        # typed API client
│       └── constants/colors.ts
│
└── lib/                      # shared TypeScript utilities
```

---

## Running locally

### Prerequisites

- Node.js 24 + pnpm (`npm i -g pnpm`)
- Python 3.11 + pip
- Redis (optional — enables task queuing and timeline streaming)

### 1. Install dependencies

```bash
pnpm install
pip install -r requirements.full.txt
```

### 2. Set environment variables

```bash
cp .env.example .env   # then fill in your keys
```

Required: `OPENAI_API_KEY` and/or `GEMINI_API_KEY`.

### 3. Start the backend

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4. Start the web frontend

```bash
PORT=20721 BASE_PATH=/ pnpm --filter @workspace/concierge run dev
```

Open [http://localhost:20721](http://localhost:20721).

### 5. Start the mobile app (optional)

```bash
pnpm --filter @workspace/concierge-mobile run dev
```

Open the Expo dev tools and scan the QR code, or press `w` for the web preview.

---

## Docker

The Dockerfile uses two stages:

1. **`frontend-builder`** — Node 24 + pnpm builds the React/Vite SPA (`BASE_PATH=/`)
2. **`runtime`** — Python 3.11-slim installs all dependencies, serves the API + built SPA on port 8000

### API only (no Redis)

```bash
docker build -t concierge-ai .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e GEMINI_API_KEY=... \
  concierge-ai
```

App is at [http://localhost:8000](http://localhost:8000).

### Full stack (API + Redis + Celery worker)

```bash
OPENAI_API_KEY=sk-... GEMINI_API_KEY=... docker compose up
```

Services started:
- `api` — FastAPI + SPA on port 8000
- `redis` — Redis 7 broker/cache on port 6379
- `worker` — Celery worker (4 concurrent, `default` + `timeline` queues)

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key for chat and embeddings |
| `GEMINI_API_KEY` | Yes* | Google Gemini API key |
| `REDIS_URL` | No | Redis connection URL (enables task queue + streaming) |
| `CELERY_BROKER_URL` | No | Celery broker (defaults to `REDIS_URL`) |
| `CELERY_RESULT_BACKEND` | No | Celery result backend (defaults to `REDIS_URL`) |
| `PORT` | Dev | Port for the Vite dev server (required by vite.config.ts) |
| `BASE_PATH` | Dev | Base URL path for the Vite dev server (required) |
| `EXPO_PUBLIC_DOMAIN` | Mobile | Backend domain for the mobile app (e.g. `your-repl.replit.dev`) |

*At least one AI key is required for the chat to respond.

---

## Architecture notes

- **API routing**: All `/api/*` traffic flows: `Replit proxy → Vite dev server (20721) → Vite proxy → uvicorn (8000)`. The `api-server` artifact uses path `/node-api` to avoid intercepting Python API traffic.
- **React deduplication**: `react`, `react-dom`, `axios`, `zustand`, and `react-router-dom` are all in `optimizeDeps.include` and `resolve.dedupe` to prevent duplicate module instances (fixes "invalid hook call" bugs).
- **Graceful Redis degradation**: Task queueing, pub/sub timeline streaming, and job history all require Redis. Without it the app stays functional but those features log errors.
- **Pages**: `React.lazy()` + Suspense for all page-level components.

---

## Mobile app

The Expo app (`artifacts/concierge-mobile/`) is a native companion to the web app.

**Screens:**
- **Chat** — full AI chat with animated message bubbles, typing indicator, haptic feedback
- **Tasks** — live task monitor polling the backend every 8 seconds, pull-to-refresh

**Connecting to the backend:**

Set `EXPO_PUBLIC_DOMAIN` to your backend's public domain before starting. In Replit this is handled automatically via the `artifact.toml` environment.

**Design tokens** (`constants/colors.ts`) mirror the web app's palette — navy `#0F172A`, blue `#2563EB`, light background `#F0F8FF`.
