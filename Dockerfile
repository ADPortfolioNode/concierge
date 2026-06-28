<<<<<<< HEAD
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Build the React/Vite frontend
# ─────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /workspace

# Enable pnpm via corepack (matches Node 24 built-in)
RUN corepack enable && corepack prepare pnpm@latest --activate
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

# Workspace manifests first — maximises layer cache on dep changes
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml .npmrc \
     tsconfig.base.json tsconfig.json ./

<<<<<<< HEAD
# Shared libs consumed by the frontend
COPY lib/ lib/

# Frontend package
COPY artifacts/concierge/ artifacts/concierge/

# Install — honour the lock file exactly.
# pnpm 9+ (corepack @latest) enforces build script approval.
# We explicitly allow all for the builder stage (trusted lockfile + Docker).
RUN pnpm config set dangerously-allow-all-builds true
RUN pnpm install --frozen-lockfile

# The pnpm-workspace.yaml aggressively disables all platform-specific
# @rollup/rollup-*, lightningcss-*, and @tailwindcss/oxide-* packages
# (to keep the Windows dev experience clean). Inside Alpine (musl) we need
# the x64-musl bindings for Vite/Rollup + Tailwind/LightningCSS + Oxide
# production build.
# Add at root (so all workspace packages can resolve the native binding via pnpm's store).
# Use -w (--workspace-root) to explicitly allow adding to root in a workspace.
RUN pnpm --filter @workspace/concierge add -D \
  @rollup/rollup-linux-x64-musl@4.59.0 \
  lightningcss-linux-x64-musl@1.31.1 \
  @tailwindcss/oxide-linux-x64-musl@4.2.1

# Re-install the workspace package (non-frozen) so the added native bindings are properly linked for the filter
RUN pnpm install --filter @workspace/concierge --no-frozen-lockfile

# Patch the installed native packages' optionalDependencies (they were stripped by workspace overrides).
# This fixes "Cannot find native binding" for oxide/rollup/lightningcss in Alpine.
RUN node -e '
const fs = require("fs");
const path = require("path");
function patch(parent, binding, ver) {
  const p = path.join("node_modules", parent, "package.json");
  if (fs.existsSync(p)) {
    const pkg = JSON.parse(fs.readFileSync(p, "utf8"));
    pkg.optionalDependencies = pkg.optionalDependencies || {};
    pkg.optionalDependencies[binding] = ver;
    fs.writeFileSync(p, JSON.stringify(pkg, null, 2));
    console.log("Patched", parent);
  }
}
patch("@tailwindcss/oxide", "@tailwindcss/oxide-linux-x64-musl", "4.2.1");
patch("lightningcss", "lightningcss-linux-x64-musl", "1.31.1");
patch("rollup", "@rollup/rollup-linux-x64-musl", "4.59.0");
'

# Production build (BASE_PATH=/ → served at root by FastAPI)
# Wrap to print the actual error on failure (Docker build often truncates)
RUN BASE_PATH=/ NODE_ENV=production sh -c 'pnpm --filter @workspace/concierge run build || (echo "=== VITE BUILD FAILED (last 100 lines) ===" && pnpm --filter @workspace/concierge run build 2>&1 | tail -100 ; exit 1)'
=======
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime image
<<<<<<< HEAD
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps needed by some Python packages (Pillow, onnxruntime, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
=======
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
<<<<<<< HEAD
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps — full set (includes Celery, Redis, ChromaDB, etc.)
COPY requirements.full.txt ./
RUN pip install --no-cache-dir -r requirements.full.txt

# ── Python source ────────────────────────────────────────────────────────────
COPY app.py main.py task_tree_store.py task_agent.py ./
COPY VERSION ./
=======
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
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5

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
<<<<<<< HEAD
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
=======
# app.py _find_static_dir() looks for frontend/dist relative to itself
COPY --from=frontend-builder /workspace/artifacts/concierge/dist/public/ \
     frontend/dist/

# ── Entrypoint ────────────────────────────────────────────────────────────────
COPY start.sh ./
RUN chmod +x start.sh

# Create writable runtime dirs and a non-root user for security
RUN mkdir -p media data \
    && addgroup --system appuser \
    && adduser --system --ingroup appuser --no-create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Gunicorn + UvicornWorker: production-grade multi-process ASGI.
# Override WORKERS (default 2), PORT, and LOG_LEVEL at runtime as needed.
CMD ["./start.sh"]
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
