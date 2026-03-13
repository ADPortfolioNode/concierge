#!/usr/bin/env bash
# simple helper to manage development containers and diagnostics
# usage: start.sh [--prune] [--yes] [--build] [--diag] [--log] [--frontend|--no-frontend] [--help]

set -euo pipefail

# make sure we actually have a bash-compatible shell; this script uses
# bash-specific features and Unix utilities.  Running it under PowerShell or
# Command Prompt silently returns without doing anything, which is confusing
# for Windows users.
if [ -z "${BASH_VERSION:-}" ]; then
    cat <<'MSG' >&2
This helper script must be executed from a Bourne-compatible shell such as
Git Bash, WSL, Cygwin, or a Linux/macOS terminal.  Launch one of those shells
and run:

    ./start.sh [options]

If you are on Windows and bash is available (e.g. Git Bash/WSL) you can also
invoke the script explicitly via:

    bash ./start.sh [options]

Direct execution from PowerShell or Command Prompt will not work because they
ignore the shebang and lack the Unix utilities used below.
MSG
    exit 1
fi

# abort on any unhandled error and report
trap 'echo "Error on line $LINENO: command failed" >&2; exit 1' ERR

# wrapper to support either docker-compose or docker compose
compose() {
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

# attempt to free any known ports that might conflict with the
# docker-compose services. this is especially helpful when a stray
# development server (vite, flask, etc.) is still running and prevents
# containers from binding their expected ports. the list below mirrors the
# ports exposed in docker-compose.yml; add or remove entries as needed.
clear_ports() {
    ports=(8000 8001 5173 6333)
    for p in "${ports[@]}"; do
        echo "checking port $p"
        if command -v lsof >/dev/null 2>&1; then
            pid=$(lsof -ti tcp:"$p" 2>/dev/null || true)
            if [ -n "$pid" ]; then
                echo "killing process $pid listening on port $p"
                kill -9 $pid || true
            fi
        elif command -v netstat >/dev/null 2>&1; then
            # awk/cut pipeline extracts PID from the -p column (Linux)
            pid=$(netstat -tulpn 2>/dev/null | grep ":$p " | awk '{print $7}' | cut -d/ -f1 || true)
            if [ -n "$pid" ]; then
                echo "killing process $pid listening on port $p"
                kill -9 $pid || true
            fi
        else
            echo "cannot check port $p (no lsof or netstat available)" >&2
        fi
    done
}

# verify prerequisites early
if ! command -v docker >/dev/null 2>&1; then
    die "docker CLI not found; please install Docker"
fi
if ! docker info >/dev/null 2>&1; then
    die "docker daemon not running or not accessible"
fi

# ensure we have a compose implementation
if ! compose version >/dev/null 2>&1; then
    die "docker compose not available (install docker-compose or use newer Docker)"
fi

default_answer="N"

die() {
    echo "$*" >&2
    exit 1
}

print_usage() {
    cat <<'USAGE'
Usage: start.sh [options]

Options:
  --prune    remove stopped containers, unused images/networks/volumes
  --yes      answer "yes" to any confirmation prompts
  --build    run `docker-compose build` before starting services
  --diag     emit a small diagnostics log (docker info, ps, etc.)
  --log      capture docker-compose service logs to start.log
  --clear    stop and remove running compose services (docker-compose down)
  --frontend      start the React frontend dev server (npm run dev) and log output (default)
  --no-frontend   do not attempt to start the frontend service
  -h, --help display this message

Examples:
  start.sh --prune --yes --build --diag  # full clean, build, and log then up
  start.sh                               # bring up compose services
  start.sh --clear                       # tear down compose services
USAGE
}

PRUNE=false
YES=false
BUILD=false
DIAG=false
LOGS=false
TEST=false
# frontend will be started by default; use --no-frontend to skip
FRONTEND=true
CLEAR=false

for arg in "$@"; do
    case "$arg" in
        --prune) PRUNE=true ;;
        --yes) YES=true ;;
        --build) BUILD=true ;;
        --diag) DIAG=true ;;
        --log) LOGS=true ;; 
        --test) TEST=true ;;
        --frontend) FRONTEND=true ;;  # explicit enable (redundant)
        --no-frontend) FRONTEND=false ;;
        --clear) CLEAR=true ;;
        -h|--help) print_usage; exit 0 ;;
        *)
            echo "Unknown option: $arg" >&2
            print_usage
            exit 1
            ;;
    esac
done

confirm() {
    local prompt="$1"
    if $YES; then
        return 0
    fi
    read -r -p "$prompt [y/N] " response
    case "$response" in
        [Yy]*) return 0 ;; 
        *) return 1 ;;
    esac
}

if $PRUNE; then
    if confirm "Prune docker system (containers/images/networks/volumes)?"; then
        echo "Pruning docker system..."
        docker system prune -af || echo "prune failed, continuing" >&2
    else
        echo "Skipping prune."
    fi
fi

if $BUILD; then
    echo "Building containers..."
    compose build || die "compose build failed"
fi

if $DIAG; then
    echo "Writing diagnostics to start.log"
    {
        echo "--- docker version ---"
        docker version || true
        echo
        echo "--- docker-compose version ---"
        docker-compose version || true
        echo
        echo "--- docker ps -a ---"
        docker ps -a || true
        echo "--- end diagnostics ---"
    } | tee start.log
fi

if $CLEAR; then
    # --clear implies restart with build to avoid stale images
    echo "Clearing environment: compose down; up -d --build"
    echo "freeing known ports before tear down/start"
    clear_ports
    compose down || true
    compose up -d --build || die "compose up failed"
else
    # always attempt to tear down first to avoid port conflicts, then bring up
    echo "freeing known ports before tear down/start"
    clear_ports
    echo "Ensuring any existing services are stopped (compose down)"
    compose down || true
    if $BUILD; then
        echo "Building containers before start..."
        compose build || die "compose build failed"
    fi
    echo "Starting services with compose up -d"
    compose up -d || die "compose up failed"
    # if user requested logging, capture an initial snapshot of backend output
    if $LOGS; then
        # give containers a moment to emit startup messages
        sleep 1
        echo "-- initial backend log snapshot --" >> start.log
        compose logs --no-color app --tail=50 >> start.log || true
        echo "-- end snapshot --" >> start.log
    fi
fi

# if --test was requested, kick off Playwright and tail backend logs
if $TEST; then
    echo "--test flag detected: launching Playwright suite and capturing logs"
    # tail logs so we can see server output during the test
    docker logs -f quesarc_app --since 1s > playwright_backend.log 2>&1 &
    LOGPID=$!
    # run tests from the embedded frontend directory; allow custom args via TEST_ARGS
    (cd frontend && npx playwright test ${TEST_ARGS:-})
    # stop log tail
    kill $LOGPID 2>/dev/null || true
    echo "Playwright run complete; backend log written to playwright_backend.log"
fi

if $FRONTEND; then
    if [ -d "frontend" ]; then
        if [ -f "frontend/package-lock.json" ]; then
            npm --prefix frontend ci --no-audit --no-fund || {
                echo "npm ci failed; falling back to npm install" >&2
                die "npm install failed"
            }
        else
            npm --prefix frontend install || {
                echo "npm install failed; check frontend/package.json for invalid version ranges (e.g. zustand)" >&2
                die "npm install failed"
            }
        fi
    else
        echo "Warning: frontend directory not found, skipping install." >&2
    fi
    echo "Starting frontend container via docker-compose"
    compose up -d frontend || die "failed to start frontend container"
    if $LOGS; then
        echo "Appending backend+frontend logs to start.log"
        compose logs --no-color app frontend | tee -a start.log
    fi
    # check status and show logs if any container exited unexpectedly
    for svc in app frontend; do
        if compose ps | grep -q "quesarc_${svc}.*Exited"; then
            echo "${svc^} container exited; here are the last 20 lines of its log:" >&2
            compose logs $svc --tail=20 >&2
        fi
    done
fi

echo "start.sh complete."
