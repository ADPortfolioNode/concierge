# ─────────────────────────────────────────────────────────────────────────────
# docker-bake.hcl — multi-platform build definition for Concierge AI
#
# Usage
# ──────
# Build both platforms locally (requires a multi-platform buildx builder):
#   docker buildx bake
#
# Build and push to a registry:
#   REGISTRY=ghcr.io/yourorg TAG=v1.2.3 docker buildx bake --push
#
# Build a single platform for local testing:
#   docker buildx bake --set api.platforms=linux/amd64 --load
#
# Set up a multi-platform builder (one-time, per machine):
#   docker buildx create --name mp-builder --driver docker-container --use
#   docker buildx inspect --bootstrap
# ─────────────────────────────────────────────────────────────────────────────

variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = ""
}

# Derive the full image name: "concierge-ai:latest" or "ghcr.io/org/concierge-ai:v1.0"
locals {
  image = REGISTRY != "" ? "${REGISTRY}/concierge-ai:${TAG}" : "concierge-ai:${TAG}"
}

# ── Default group — builds everything ────────────────────────────────────────
group "default" {
  targets = ["api"]
}

# ── API + SPA image ──────────────────────────────────────────────────────────
target "api" {
  context    = "."
  dockerfile = "Dockerfile"
  target     = "runtime"

  platforms = [
    "linux/amd64",
    "linux/arm64",
  ]

  tags = [local.image]

  # GitHub Actions cache (change type=local for local disk cache)
  cache-from = ["type=gha,scope=concierge-api"]
  cache-to   = ["type=gha,mode=max,scope=concierge-api"]

  args = {
    PNPM_VERSION = "9.15.4"
  }
}

# ── Local-only single-platform shortcut (loads into local Docker daemon) ─────
# Usage: docker buildx bake local
target "local" {
  inherits  = ["api"]
  platforms = ["linux/amd64"]
  tags      = ["concierge-ai:dev"]
  # Swap GHA cache for a local directory cache so this works off-CI
  cache-from = ["type=local,src=/tmp/buildx-cache"]
  cache-to   = ["type=local,dest=/tmp/buildx-cache,mode=max"]
  output     = ["type=docker"]
}
