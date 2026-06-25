# ─────────────────────────────────────────────────────────────────────────────
# Concierge AI — Docker Compose
#
# Profiles
#   (default)   → api only — Redis not required, tasks run inline
#   full        → api + redis broker + celery worker
#
# Quick start (API + SPA, no Redis):
#   docker compose up --build
#
# Full stack (API + Redis + Celery worker):
#   docker compose --profile full up --build
#
# Environment — copy .env.example to .env and fill in secrets
# ─────────────────────────────────────────────────────────────────────────────

x-app-env: &app-env
  OPENAI_API_KEY:       ${OPENAI_API_KEY:-}
  ANTHROPIC_API_KEY:    ${ANTHROPIC_API_KEY:-}
  GEMINI_API_KEY:       ${GEMINI_API_KEY:-}
  REDIS_URL:            ${REDIS_URL:-redis://redis:6379/0}
  CELERY_BROKER_URL:    ${CELERY_BROKER_URL:-redis://redis:6379/0}
  CELERY_RESULT_BACKEND: ${CELERY_RESULT_BACKEND:-redis://redis:6379/0}
  PORT:                 "8000"
  WORKERS:              ${WORKERS:-2}
  LOG_LEVEL:            ${LOG_LEVEL:-info}

services:

  # ── API + SPA (always starts) ───────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    image: concierge-ai:latest
    ports:
      - "${HOST_PORT:-8000}:8000"
    environment:
      <<: *app-env
    volumes:
      - media_data:/app/media
      - app_data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/_health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    # No depends_on for redis (graceful degradation in app.py)

  # ── Redis (only with --profile full) ────────────────────────────────────────
  redis:
    profiles: [full]
    image: redis:7-alpine
    command: redis-server --save 60 1 --loglevel warning
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Celery worker (only with --profile full) ────────────────────────────────
  worker:
    profiles: [full]
    image: concierge-ai:latest
    command: >
      celery -A tasks.main_tasks worker
        --loglevel=${LOG_LEVEL:-info}
        --concurrency=${CELERY_CONCURRENCY:-4}
        --queues=default,timeline
    environment:
      <<: *app-env
    volumes:
      - media_data:/app/media
      - app_data:/app/data
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis_data:
  media_data:
  app_data: