<<<<<<< HEAD
# Use official lightweight Python image
###
# Multi-stage Dockerfile
# - Optional `frontend` build stage (Node) when ARG BUILD_FRONTEND=1
# - Python runtime image installs either `requirements.txt` or the fuller
#   `requirements.full.txt` when ARG INSTALL_FULL_REQUIREMENTS=1 is passed.
# - Accepts `VITE_API_URL` as a build-arg so frontend builds embed the right
#   API URL at build-time (Vite injects VITE_* envs during build).
###

ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE} AS base

# Prevent Python from writing .pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install minimal system dependencies needed to compile native wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

### Optional frontend build stage (Node) ###############################
ARG BUILD_FRONTEND=0
ARG VITE_API_URL=""
ARG VITE_API_URL_DOCKER=""
FROM node:18-alpine AS frontend-build
WORKDIR /build
# Ensure devDependencies like Vite are installed for the frontend build
ENV NODE_ENV=development
# copy only frontend sources for better cache
COPY frontend/package.json frontend/package-lock.json ./
# Ensure devDependencies like Vite are installed for the frontend build
RUN npm ci --no-audit --no-fund --include=dev
COPY frontend ./
# pass VITE_API_URL or VITE_API_URL_DOCKER as an env var during build so Vite picks it up
ARG VITE_API_URL
ARG VITE_API_URL_DOCKER
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_API_URL_DOCKER=${VITE_API_URL_DOCKER}
RUN if [ "${BUILD_FRONTEND}" = "1" ]; then \
        if [ -z "$VITE_API_URL" ] && [ -n "$VITE_API_URL_DOCKER" ]; then export VITE_API_URL="$VITE_API_URL_DOCKER"; fi && npm run build --if-present; \
    else \
        echo "Skipping frontend build because BUILD_FRONTEND is not '1'." && \
        mkdir -p /build/dist; \
    fi

### Final runtime image ###############################################
FROM base AS runtime

# Build args to control install behavior
ARG INSTALL_FULL_REQUIREMENTS=0

# Copy requirements
COPY requirements.txt ./
COPY requirements.full.txt ./

# Upgrade pip and install requirements; prefer full if requested and present
RUN pip install --upgrade pip
RUN if [ "${INSTALL_FULL_REQUIREMENTS}" = "1" ] && [ -f requirements.full.txt ]; then \
            pip install -r requirements.full.txt ; \
        else \
            pip install -r requirements.txt ; \
        fi

# Copy application code
COPY . .

# Copy built frontend assets from the build stage (if present)
COPY --from=frontend-build /build/dist /app/frontend_dist

# Expose the app port for self-contained Docker distribution
EXPOSE 8000

# Default command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
=======
# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Multi-platform build: linux/amd64  linux/arm64
#
#   docker buildx bake                          # both platforms, local load
#   docker buildx bake --push                   # push to registry
#   docker buildx build --platform linux/arm64 . # single platform, quick test
#
# BUILDPLATFORM  = the machine running the build  (e.g. linux/amd64 on x86 CI)
# TARGETPLATFORM = the platform the image will run on
# ─────────────────────────────────────────────────────────────────────────────

# Declare build-time platform args (injected automatically by buildx)
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Build the React/Vite frontend
#
# Pin to BUILDPLATFORM so Node runs natively on the build host.
# Vite output is pure JS/CSS — no arch-specific bytes — so the artefact is
# identical regardless of which arch compiled it.  Running under QEMU for a
# cross-arch Node build would be 5–10× slower with no benefit.
# ─────────────────────────────────────────────────────────────────────────────
FROM --platform=$BUILDPLATFORM node:24-alpine AS frontend-builder

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

# pnpm store cache is keyed to BUILDPLATFORM so amd64 and arm64 CI runners
# never share a cache that could contain arch-specific native bindings.
ARG BUILDPLATFORM
RUN --mount=type=cache,id=pnpm-store-${BUILDPLATFORM},target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Production build (BASE_PATH=/ → SPA served at root by FastAPI)
RUN BASE_PATH=/ NODE_ENV=production \
    pnpm --filter @workspace/concierge run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime image
#
# No explicit --platform here; buildx sets TARGETPLATFORM automatically and
# pulls the correct python:3.11-slim-bookworm manifest (amd64 or arm64).
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

# Sensible Python container defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Permanent runtime system libs (Pillow, onnxruntime, chromadb shared objects).
# All packages are available in Debian Bookworm for both amd64 and arm64.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps.
# build-essential compiles any wheels without pre-built binaries (rare on 3.11)
# and is removed in the same layer so it doesn't land in the final image.
#
# pip cache is keyed to TARGETPLATFORM — amd64 and arm64 runners stay isolated
# because wheel files are architecture-specific.
#
# onnxruntime ships amd64 + arm64 wheels on PyPI since v1.16 — no special
# handling needed.  chromadb and all other deps likewise supply both arches.
ARG TARGETPLATFORM
COPY requirements.prod.txt ./
RUN --mount=type=cache,id=pip-${TARGETPLATFORM},target=/root/.cache/pip \
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
>>>>>>> ba3e36e0566fb095502dfcaddb8195433f4c9f1a
