# ─────────────────────────────────────────────────────────────────────────────
# Concierge AI — Makefile
# Requires: Docker Desktop (includes buildx + compose)
# ─────────────────────────────────────────────────────────────────────────────

# Auto-detect the native arch of the machine running the build.
# Docker Desktop uses this to pick the right base image layer — no emulation.
ARCH   := $(shell uname -m)
ifeq ($(ARCH),arm64)
  NATIVE_PLATFORM := linux/arm64
else
  NATIVE_PLATFORM := linux/amd64
endif

# Registry / tag — override on the command line:
#   make push REGISTRY=docker.io/yourname TAG=v1.2.3
REGISTRY ?=
TAG      ?= latest

# ── Help ──────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
.PHONY: help build up up-full down push shell logs clean

help:
	@echo ""
	@echo "  Concierge AI — Docker Desktop commands"
	@echo ""
	@echo "  make build          Build image for this machine ($(NATIVE_PLATFORM))"
	@echo "  make up             Start API + SPA  (no Redis)"
	@echo "  make up-full        Start API + Redis + Celery worker"
	@echo "  make down           Stop and remove containers"
	@echo "  make push           Build linux/amd64 + linux/arm64 and push to REGISTRY"
	@echo "  make shell          Open a shell inside the running api container"
	@echo "  make logs           Tail logs from all running containers"
	@echo "  make clean          Remove the image and build cache"
	@echo ""
	@echo "  Variables: REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo ""

# ── Build ─────────────────────────────────────────────────────────────────────

## Build a single-platform image matching this machine and load it into Docker Desktop.
build:
	LOCAL_PLATFORM=$(NATIVE_PLATFORM) TAG=$(TAG) REGISTRY=$(REGISTRY) \
	  docker buildx bake local

# ── Run ───────────────────────────────────────────────────────────────────────

## Start the API + SPA only (Redis not required; tasks run inline).
up:
	docker compose up

## Start the full stack: API + Redis broker + Celery worker.
up-full:
	docker compose --profile full up

## Stop and remove all containers (data volumes are preserved).
down:
	docker compose --profile full down

# ── Logs / shell ──────────────────────────────────────────────────────────────

## Tail live logs from all running Compose services.
logs:
	docker compose logs -f

## Open an interactive shell inside the running api container.
shell:
	docker compose exec api sh

# ── Push ──────────────────────────────────────────────────────────────────────

## Build linux/amd64 + linux/arm64 and push a multi-arch manifest to REGISTRY.
## Usage: make push REGISTRY=docker.io/yourname TAG=v1.0
push:
	@if [ -z "$(REGISTRY)" ]; then \
	  echo "Error: REGISTRY is not set. Usage: make push REGISTRY=docker.io/yourname"; \
	  exit 1; \
	fi
	REGISTRY=$(REGISTRY) TAG=$(TAG) docker buildx bake push

# ── Clean ─────────────────────────────────────────────────────────────────────

## Remove the local image and wipe the local BuildKit layer cache.
clean:
	docker rmi concierge-ai:dev concierge-ai:$(TAG) 2>/dev/null || true
	rm -rf /tmp/buildx-cache/concierge
