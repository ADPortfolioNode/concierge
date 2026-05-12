# ─────────────────────────────────────────────────────────────────────────────
# docker-bake.hcl — multi-platform build definition for Concierge AI
#
# Docker Desktop already includes a multi-platform buildx builder.
# No "docker buildx create" step is needed.
#
# Common commands (see Makefile for shortcuts):
#
#   Local build & run (matches your machine's native arch):
#     make build          # → docker buildx bake local
#     make up             # → docker compose up
#
#   Push multi-arch image to a registry:
#     make push REGISTRY=docker.io/yourname TAG=v1.0
#
#   Override the local platform explicitly:
#     LOCAL_PLATFORM=linux/arm64 docker buildx bake local
# ─────────────────────────────────────────────────────────────────────────────

# ── Variables ─────────────────────────────────────────────────────────────────

variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = ""
}

# The platform to build & load into the local Docker Desktop daemon.
# Makefile auto-detects this from `uname -m`; override here if needed.
#   Apple Silicon (M1/M2/M3) → linux/arm64
#   Intel Mac / Windows / Linux x86 → linux/amd64
variable "LOCAL_PLATFORM" {
  default = "linux/amd64"
}

variable "PNPM_VERSION" {
  default = "9.15.4"
}

# ── Locals ────────────────────────────────────────────────────────────────────

locals {
  # "concierge-ai:latest"  or  "ghcr.io/org/concierge-ai:v1.0"
  image = REGISTRY != "" ? "${REGISTRY}/concierge-ai:${TAG}" : "concierge-ai:${TAG}"
}

# ── Default group ─────────────────────────────────────────────────────────────

group "default" {
  targets = ["local"]
}

# ── Shared build args ─────────────────────────────────────────────────────────

target "_base" {
  context    = "."
  dockerfile = "Dockerfile"
  target     = "runtime"
  args = {
    PNPM_VERSION = PNPM_VERSION
  }
}

# ── local — single-platform, loads straight into Docker Desktop daemon ────────
#
# This is the everyday dev target.  It builds for LOCAL_PLATFORM only
# (auto-set by Makefile to match your machine) and loads the image into
# Docker Desktop so you can immediately `docker compose up` or `docker run`.
#
# Multi-arch images can't be --load'd; use the `push` target for those.

target "local" {
  inherits  = ["_base"]
  platforms = [LOCAL_PLATFORM]
  tags      = ["concierge-ai:dev", local.image]
  output    = ["type=docker"]

  # Persistent local layer cache — speeds up repeated local builds
  cache-from = ["type=local,src=/tmp/buildx-cache/concierge"]
  cache-to   = ["type=local,dest=/tmp/buildx-cache/concierge,mode=max"]
}

# ── push — both platforms, pushes a multi-arch manifest to a registry ─────────
#
# Requires REGISTRY to be set.  Uses GitHub Actions cache when running in CI
# (ACTIONS_CACHE_URL is set automatically); falls back to registry cache locally.
#
# Usage:
#   REGISTRY=docker.io/yourname TAG=v1.0 docker buildx bake push

target "push" {
  inherits = ["_base"]
  platforms = [
    "linux/amd64",
    "linux/arm64",
  ]
  tags = [local.image]

  cache-from = [
    "type=gha,scope=concierge-api",
    "type=registry,ref=${local.image}-cache",
  ]
  cache-to = [
    "type=gha,mode=max,scope=concierge-api",
  ]
}
