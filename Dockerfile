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
COPY VERSION ./

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
