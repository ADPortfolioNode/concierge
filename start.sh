#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Concierge AI - Optimized start.sh
#
# DEFAULT: Full production build + run (recommended for production)
#   ./start.sh
#   -> Builds the complete production image (frontend built via Dockerfile)
#   -> Starts API + bundled SPA on :8000
#
# Production build by default means:
#   - Multi-stage Docker build (pnpm build of React + Python runtime)
#   - No dev servers / --reload
#   - Uses the production CMD in Dockerfile
#
# FLAGS for various configurations:
#   --full              Add Redis + Celery worker (--profile full)
#   --dev               Local development (pnpm dev:frontend + dev:backend)
#   --local             Bare Python + frontend (no Docker at all)
#   --build             Force rebuild images / frontend
#   --no-build          Skip build step (use existing images)
#   --clean             Full clean: docker compose down -v --remove-orphans first
#   --test              Run tests after stack is up (Playwright by default)
#   --no-frontend       Do not start the frontend service (API only)
#   --docker-dev        Force Docker even in --dev mode (volumes for live edit)
#   --help              Show this help
#
# Examples:
#   ./start.sh                      # Production build + run (default)
#   ./start.sh --full               # Production + Redis + worker
#   ./start.sh --dev                # Fast local dev
#   ./start.sh --local --build      # Bare metal production-like
#   ./start.sh --test               # Production build then run tests
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Defaults (production build oriented) ---
MODE="prod"
PROFILE=""
BUILD_FLAG="--build"
DO_CLEAN=false
RUN_TEST=false
NO_FRONTEND=false
FORCE_DOCKER_DEV=false
SHOW_HELP=false

# --- Parse flags ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full)             PROFILE="full"; COMPOSE_PROFILES_ARG="full"; shift ;;
    --dev)              MODE="dev"; shift ;;
    --local)            MODE="local"; shift ;;
    --build)            BUILD_FLAG="--build"; shift ;;
    --no-build)         BUILD_FLAG=""; shift ;;
    --clean)            DO_CLEAN=true; shift ;;
    --test)             RUN_TEST=true; shift ;;
    --no-frontend)      NO_FRONTEND=true; shift ;;
    --docker-dev)       FORCE_DOCKER_DEV=true; shift ;;
    --help|-h)          SHOW_HELP=true; shift ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage."
      exit 1
      ;;
  esac
done

if [[ "$SHOW_HELP" == true ]]; then
  sed -n '1,/^# ====/p' "$0" | sed 's/^# //; s/^#//'
  exit 0
fi

# --- Helper: docker compose vs docker-compose ---
# Compose v2 plugin ("docker compose") is required for --profile / --full.
# Legacy docker-compose v1 does not support profiles and will error with
# "unknown flag: --profile". Never pass --profile to v1.
COMPOSE_PROFILES_ARG=""
# Docker CLI for Compose v2 plugin (Git Bash on Windows may need docker.exe).
DOCKER_BIN="docker"
compose_v2_available() {
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  if docker compose version >/dev/null 2>&1; then
    DOCKER_BIN="docker"
    return 0
  fi
  if command -v docker.exe >/dev/null 2>&1 && docker.exe compose version >/dev/null 2>&1; then
    DOCKER_BIN="docker.exe"
    return 0
  fi
  return 1
}

has_docker() {
  compose_v2_available || command -v docker-compose >/dev/null 2>&1
}

compose_supports_profiles() {
  compose_v2_available
}

# Run compose. Uses COMPOSE_PROFILES_ARG when --full was passed.
compose_cmd() {
  if compose_v2_available; then
    if [[ -n "$COMPOSE_PROFILES_ARG" ]]; then
      "$DOCKER_BIN" compose --profile "$COMPOSE_PROFILES_ARG" "$@"
    else
      "$DOCKER_BIN" compose "$@"
    fi
    return
  fi
  if [[ -n "$COMPOSE_PROFILES_ARG" ]]; then
    echo "ERROR: --full requires Docker Compose v2 (docker compose), not legacy docker-compose."
    echo "       Run: docker compose --profile full up --build -d"
    exit 1
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
    return
  fi
  echo "ERROR: Docker Compose not found."
  exit 1
}

check_docker_daemon() {
  # Only call when we believe we have a docker CLI.
  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker CLI found but the engine/daemon is not responding."
    echo ""
    echo "On Windows (PowerShell):"
    echo "  1. Open Docker Desktop"
    echo "  2. Wait for the whale icon in the tray to show the engine is running"
    echo "     (no red error banner, 'Docker Desktop is running' in the UI)"
    echo "  3. Confirm in a terminal:  docker ps"
    echo "     It should succeed and list containers (or be empty)."
    echo "  4. Re-run your command:"
    echo "       docker compose --profile full up --build -d"
    echo "     or"
    echo "       ./start.sh --full"
    echo ""
    echo "Common cause of the exact error you saw:"
    echo "  open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
    echo ""
    exit 1
  fi
}

# --- Main logic ---
echo "=== Concierge start.sh ==="
echo "Mode: $MODE   Profile: ${PROFILE:-none}   Build: ${BUILD_FLAG:-no-build}"

if [[ "$DO_CLEAN" == true ]]; then
  echo "==> Cleaning stack..."
  if has_docker; then
    # Tear down profile services (redis/worker/flower) so network/volumes release.
    if [[ -n "$COMPOSE_PROFILES_ARG" ]]; then
      compose_cmd down -v --remove-orphans || true
    else
      # No --full: still try full profile down first to clear leftover workers.
      if compose_v2_available; then
        "$DOCKER_BIN" compose --profile full down -v --remove-orphans 2>/dev/null || true
      fi
      compose_cmd down -v --remove-orphans || true
    fi
  fi
  if [[ "$MODE" == "dev" || "$MODE" == "local" ]]; then
    rm -rf frontend/dist artifacts/concierge/dist 2>/dev/null || true
  fi
fi

case "$MODE" in
  prod)
    if ! has_docker; then
      echo "ERROR: Docker is required for production mode. Use --dev or --local instead."
      exit 1
    fi
    check_docker_daemon

    if [[ -n "$PROFILE" ]] && ! compose_supports_profiles; then
      echo "ERROR: --full requires Docker Compose v2 (the 'docker compose' plugin)."
      echo ""
      echo "The --full profile (Redis + Celery worker + flower) needs Compose v2+."
      echo ""
      echo "On Windows (recommended):"
      echo "  1. Use Docker Desktop and confirm:  docker compose version"
      echo "  2. Then run:"
      echo "       docker compose --profile full up --build -d"
      echo ""
      echo "Legacy 'docker-compose' (v1) does not support --profile."
      exit 1
    fi

    echo "==> Starting FULL PRODUCTION BUILD (default)"
    echo "    Using Dockerfile multi-stage build (frontend + Python runtime)"
    if [[ "$NO_FRONTEND" == true ]]; then
      # Note: there is no separate frontend service anymore; api serves the SPA.
      if [[ -n "$PROFILE" ]]; then
        compose_cmd up $BUILD_FLAG -d api redis worker
      else
        compose_cmd up $BUILD_FLAG -d api
      fi
    else
      compose_cmd up $BUILD_FLAG -d
    fi
    echo "==> Production stack is up (or building)."
    echo "    Access UI at http://localhost:${HOST_PORT:-8000}"
    ;;

  dev)
    echo "==> Local development mode"
    if [[ "$FORCE_DOCKER_DEV" == true ]] && has_docker; then
      check_docker_daemon
      if [[ -n "$PROFILE" ]] && ! compose_supports_profiles; then
        echo "ERROR: --full requires Docker Compose v2 (docker compose)."
        echo "Use: docker compose --profile full up --build -d instead."
        exit 1
      fi
      echo "    Using Docker with live mounts (dev containers)"
      compose_cmd up --build -d
    else
      if ! command -v pnpm >/dev/null 2>&1; then
        echo "pnpm not found. Falling back to Docker dev mode."
        if has_docker; then
          if [[ -n "$PROFILE" ]] && ! compose_supports_profiles; then
            echo "ERROR: --full requires Docker Compose v2 (docker compose)."
            exit 1
          fi
          compose_cmd up --build -d
        else
          echo "ERROR: Neither pnpm nor Docker available."
          exit 1
        fi
      else
        echo "    Starting pnpm dev:frontend + dev:backend"
        (cd . && pnpm dev:backend) &
        BACKEND_PID=$!
        pnpm dev:frontend
        kill $BACKEND_PID 2>/dev/null || true
      fi
    fi
    ;;

  local)
    echo "==> Bare local mode (no Docker)"
    echo "    Will build frontend (production) then run uvicorn (no reload)"

    if ! command -v pnpm >/dev/null 2>&1; then
      echo "ERROR: pnpm is required for --local mode."
      exit 1
    fi
    if ! command -v python >/dev/null 2>&1; then
      echo "ERROR: python is required for --local mode."
      exit 1
    fi

    echo "==> Building frontend for production..."
    pnpm build:frontend

    echo "==> Starting backend (production config - no reload)"
    exec python -m uvicorn app:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${WORKERS:-2}" \
      --log-level "${LOG_LEVEL:-info}"
    ;;

  *)
    echo "Unknown mode: $MODE"
    exit 1
    ;;
esac

if [[ "$RUN_TEST" == true ]]; then
  echo "==> Running tests..."
  if has_docker && [[ "$MODE" == "prod" ]]; then
    TEST_ARGS="${TEST_ARGS:-tests/}"
    compose_cmd exec -T api python -m pytest $TEST_ARGS || true
  else
    if command -v pnpm >/dev/null 2>&1; then
      pnpm --filter @workspace/concierge test || true
    fi
  fi
fi

echo "==> Done."
