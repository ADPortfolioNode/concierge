<<<<<<< HEAD
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
    --full)             PROFILE="--profile full"; shift ;;
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
# Prefer modern Compose v2 (supports --profile for the "full" stack).
# We check via the docker cli first for robustness in Git Bash / MINGW64 + Docker Desktop.
DC=""
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
fi

has_docker() {
  [[ -n "$DC" ]]
}

# Returns 0 if the current $DC supports --profile (Compose v2+)
supports_profiles() {
  if [[ -z "${DC:-}" ]]; then
    return 1
  fi
  if [[ "$DC" == "docker compose" ]]; then
    return 0
  fi
  # docker-compose: check version string or --help for the flag
  if $DC version --short 2>/dev/null | grep -qE '^[2-9]'; then
    return 0
  fi
  if $DC --help 2>&1 | grep -q -- '--profile'; then
    return 0
  fi
  return 1
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
    $DC down -v --remove-orphans || true
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

    # Force modern Compose when a profile is requested (Git Bash + Docker Desktop
    # sometimes makes the early detection pick the legacy docker-compose binary).
    if [[ -n "$PROFILE" ]] && docker compose version >/dev/null 2>&1; then
      DC="docker compose"
    fi

    if [[ -n "$PROFILE" ]] && ! supports_profiles; then
      echo "ERROR: Detected compose command '$DC' does not support the --profile flag."
      echo ""
      echo "The --full profile (Redis + Celery worker + flower) requires Docker Compose v2+."
      echo ""
      echo "On Windows (recommended):"
      echo "  1. Use the Docker Compose plugin that comes with Docker Desktop:"
      echo "       docker compose --profile full up --build -d"
      echo ""
      echo "  2. Or ensure 'docker compose version' succeeds in this shell."
      echo "     If you are in Git Bash / MSYS, make sure Docker is in PATH."
      echo ""
      echo "  3. Old 'docker-compose' (v1) will show 'unknown flag: --profile'."
      echo ""
      echo "Tip: You can also run the command directly without start.sh."
      exit 1
    fi

    echo "==> Starting FULL PRODUCTION BUILD (default)"
    echo "    Using Dockerfile multi-stage build (frontend + Python runtime)"
    if [[ -n "$PROFILE" ]] && docker compose version >/dev/null 2>&1; then
      # Force the modern 'docker compose' (v2) when a profile is requested.
      # This works around flaky detection in Git Bash / MINGW64 even when
      # 'docker compose' works when typed directly.
      CMD="docker compose up $PROFILE $BUILD_FLAG -d"
    else
      CMD="$DC up $PROFILE $BUILD_FLAG -d"
    fi
    if [[ "$NO_FRONTEND" == true ]]; then
      # Note: there is no separate frontend service anymore; api serves the SPA.
      # With profile we explicitly bring up the worker services.
      if [[ -n "$PROFILE" ]] && docker compose version >/dev/null 2>&1; then
        docker compose up $PROFILE $BUILD_FLAG -d api redis worker
      elif [[ -n "$PROFILE" ]]; then
        $DC up $PROFILE $BUILD_FLAG -d api redis worker
      else
        $DC up $BUILD_FLAG -d api
      fi
    else
      eval "$CMD"
    fi
    echo "==> Production stack is up (or building)."
    echo "    Access UI at http://localhost:${HOST_PORT:-8000}"
    ;;

  dev)
    echo "==> Local development mode"
    if [[ "$FORCE_DOCKER_DEV" == true ]] && has_docker; then
      check_docker_daemon
      if [[ -n "$PROFILE" ]] && docker compose version >/dev/null 2>&1; then
        DC="docker compose"
      fi
      if [[ -n "$PROFILE" ]] && ! supports_profiles; then
        echo "ERROR: Detected compose command '$DC' does not support --profile (needed for --full)."
        echo "Use: docker compose --profile full up --build -d instead."
        exit 1
      fi
      echo "    Using Docker with live mounts (dev containers)"
      $DC up $PROFILE --build -d
    else
      if ! command -v pnpm >/dev/null 2>&1; then
        echo "pnpm not found. Falling back to Docker dev mode."
        if has_docker; then
          if [[ -n "$PROFILE" ]] && ! supports_profiles; then
            echo "ERROR: Detected compose command '$DC' does not support --profile."
            exit 1
          fi
          $DC up $PROFILE --build -d
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
    $DC exec -T api python -m pytest $TEST_ARGS || true
  else
    if command -v pnpm >/dev/null 2>&1; then
      pnpm --filter @workspace/concierge test || true
    fi
  fi
fi

echo "==> Done."
=======
#!/bin/sh
set -e

exec gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WORKERS:-2}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --log-level "${LOG_LEVEL:-info}"
>>>>>>> f665b8188591020c7f82f8a93d3211e3cc2ffcb5
