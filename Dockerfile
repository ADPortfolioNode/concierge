# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Build the React/Vite frontend
# ─────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /workspace

ARG PNPM_VERSION=9.15.4
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate

# Workspace manifests first — maximises layer cache on dep changes
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml .npmrc \
     tsconfig.base.json tsconfig.json ./

# Shared workspace libs consumed by the frontend (e.g. @workspace/api-client-react)
COPY lib/ lib/

# Frontend source
COPY artifacts/concierge/ artifacts/concierge/

# Install with BuildKit pnpm store cache — fast rebuilds when deps unchanged
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Production build (BASE_PATH=/ → SPA served at root by FastAPI)
RUN BASE_PATH=/ NODE_ENV=production \
    pnpm --filter @workspace/concierge run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

# Sensible Python container defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Permanent runtime system libs (Pillow, onnxruntime, chromadb shared objects)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps.
# build-essential is needed to compile some wheels (chromadb, onnxruntime C ext)
# but is removed in the same layer so it doesn't bloat the final image.
# BuildKit pip cache avoids re-downloading on source-only changes.
COPY requirements.prod.txt ./
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install -r requirements.prod.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Python source ─────────────────────────────────────────────────────────────
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
# app.py _find_static_dir() looks for frontend/dist relative to itself
COPY --from=frontend-builder /workspace/artifacts/concierge/dist/public/ \
     frontend/dist/

# Create writable runtime dirs and a non-root user for security
RUN mkdir -p media data \
    && addgroup --system appuser \
    && adduser --system --ingroup appuser --no-create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Gunicorn + UvicornWorker: production-grade multi-process ASGI.
# Override WORKERS (default 2) and LOG_LEVEL at runtime as needed.
CMD ["sh", "-c", \
     "gunicorn app:app \
       --worker-class uvicorn.workers.UvicornWorker \
       --workers ${WORKERS:-2} \
       --bind 0.0.0.0:${PORT:-8000} \
       --timeout 120 \
       --graceful-timeout 30 \
       --access-logfile - \
       --log-level ${LOG_LEVEL:-info}"]
