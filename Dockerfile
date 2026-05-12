<<<<<<< HEAD
# --- Build Stage ---
# Use a specific Python version for reproducibility.
FROM python:3.11-slim as builder

# Set environment variables to ensure clean and predictable builds.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies
# This leverages Docker's layer caching.
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# --- Final Stage ---
# Use a minimal, non-root base image for security.
FROM python:3.11-slim
WORKDIR /app

# Copy dependencies from the build stage.
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the application source code.
COPY . .

# Command to run the application with live reload for development.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
=======
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Build the React/Vite frontend
# ─────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /workspace

# Enable pnpm via corepack (matches Node 24 built-in)
RUN corepack enable && corepack prepare pnpm@latest --activate

# Workspace manifests first — maximises layer cache on dep changes
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml .npmrc \
     tsconfig.base.json tsconfig.json ./

# Shared libs consumed by the frontend
COPY lib/ lib/

# Frontend package
COPY artifacts/concierge/ artifacts/concierge/

# Install — honour the lock file exactly
RUN pnpm install --frozen-lockfile

# Production build (BASE_PATH=/ → served at root by FastAPI)
RUN BASE_PATH=/ NODE_ENV=production \
    pnpm --filter @workspace/concierge run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps needed by some Python packages (Pillow, onnxruntime, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps — full set (includes Celery, Redis, ChromaDB, etc.)
COPY requirements.full.txt ./
RUN pip install --no-cache-dir -r requirements.full.txt

# ── Python source ────────────────────────────────────────────────────────────
COPY app.py main.py task_tree_store.py task_agent.py ./

COPY agents/        agents/
COPY api/           api/
COPY config/        config/
COPY core/          core/
COPY data/          data/
COPY gateway/       gateway/
COPY integrations/  integrations/
COPY jobs/          jobs/
COPY memory/        memory/
COPY orchestration/ orchestration/
COPY plugins/       plugins/
COPY quesarc/       quesarc/
COPY rendr/         rendr/
COPY scripts/       scripts/
COPY tasks/         tasks/
COPY tools/         tools/
COPY workstation/   workstation/

# ── Built frontend ───────────────────────────────────────────────────────────
# app.py's _find_static_dir() looks for frontend/dist relative to itself.
# Copy the Vite output there so the SPA is served by FastAPI on port 8000.
COPY --from=frontend-builder /workspace/artifacts/concierge/dist/public/ \
     frontend/dist/

# Writable runtime directory for uploaded media
RUN mkdir -p media

# ─────────────────────────────────────────────────────────────────────────────
EXPOSE 8000

# Default: API + SPA server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
>>>>>>> 63023efe998310626d5b38225a84098520cb9ceb
