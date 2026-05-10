#!/usr/bin/env bash
# simple helper to manage development containers and diagnostics
# usage: start.sh [--prune] [--yes] [--build] [--diag] [--log] [--frontend|--no-frontend] [--fresh] [--pause] [--input-flags] [--help]

set -euo pipefail

if [ -f "version" ]; then
    # Read version and remove any leading/trailing whitespace
    APP_VERSION=$(cat version | tr -d '[:space:]')
else
    APP_VERSION="unknown"
fi
export APP_VERSION
echo "=== Concierge v${APP_VERSION} ==="
echo "Backend → http://localhost:8000"
echo "Frontend → http://localhost:5173"
echo "Flower → http://localhost:5555"
echo "ChromaDB (on port 8001) volume enabled for persistent memory"

print_completion_urls() {
    echo ""
    echo "=== Concierge is running ==="
    if ! $NO_DOCKER; then # Docker mode
        echo "  Backend  → http://localhost:8000"
        echo "  Frontend → http://localhost:5173"
        echo "  Flower   → http://localhost:5555 (Celery Monitor)"
        echo "  ChromaDB → http://localhost:8001 (Vector DB)"
    else # Local mode
        echo "  Backend  → http://localhost:8000"
        if $FRONTEND; then
            echo "  Frontend → http://localhost:5173"
        fi
        echo "  (Docker services like Flower and ChromaDB are not running in --no-docker mode)"
    fi
    local ngrok_url
    if ngrok_url=$(get_ngrok_public_url); then
        if [ -n "$ngrok_url" ]; then
            echo "  Public URL (ngrok) → ${ngrok_url}"
        fi
    fi
    echo ""
}
# make sure we actually have a bash-compatible shell; this script uses

open_browser() {
    local url="${1:-}"
    echo "Attempting to open browser to: $url"
    local py
    if py=$(find_python); then
        # Delegate to the shared core.browser utility to ensure consistency
        # across all startup paths.
        $py -m core.browser "$url" >/dev/null 2>&1 &
    else
        # Fallback for environments where Python isn't found
        if command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" &
        elif command -v open >/dev/null 2>&1; then open "$url" &
        else echo "Warning: Python not found. Please visit $url manually." >&2; fi
    fi
}

# bash-specific features and Unix utilities.  Running it under PowerShell or
# Command Prompt silently returns without doing anything, which is confusing
# for Windows users.
if [ -z "${BASH_VERSION:-}" ]; then
    cat <<'MSG' >&2
This helper script must be executed from a Bourne-compatible shell such as
Git Bash, WSL, Cygwin, or a Linux/macOS terminal.  Launch one of those shells
and run:

    ./start.sh [options]

If you are on Windows and have a Bash-compatible environment (Git Bash or
WSL) you can invoke the script explicitly via:

    bash ./start.sh [options]

If you are running plain PowerShell or Command Prompt, this script will not
work because those shells do not provide the Unix utilities and shell
features used here.  Instead, either run the script from Git Bash/WSL or use
the equivalent PowerShell commands shown below.

Quick PowerShell equivalents (examples) -- run these from an elevated
PowerShell session in the repository root:

# 1) Free a port (example: 8001)
netstat -ano | findstr :8001
# if a PID is listed, stop it:
Stop-Process -Id <PID> -Force

# 2) Ensure Docker is running and start compose services
docker compose up -d

# 3) Install and start the frontend dev server (optional local dev)
cd frontend
npm install --no-audit --no-fund
npm run dev

If you want a full, identical run of this helper on Windows, open Git Bash or
WSL and run the script there.  Example (Git Bash):

    ./start.sh --prune --yes --build --log

Direct execution from PowerShell or Command Prompt will not work because they
ignore the shebang and lack the Unix utilities used below.
MSG
    exit 1
fi

# abort on any unhandled error and report
trap 'echo "Error on line $LINENO: command failed" >&2; exit 1' ERR

# wrapper to support either docker-compose or docker compose
compose() { # Function to abstract docker-compose vs docker compose
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

# Global PIDs for background processes to be cleaned up on exit
COMPOSE_LOGS_PID=""
PLAYWRIGHT_LOG_PID=""
BACKEND_LOG_TAIL_PID=""
BACKEND_PID=""
FRONTEND_PID=""

FRONTEND_PORT="5173" # Default, will be updated by get_frontend_port_from_log

# Define a cleanup function to be called on exit
_cleanup_on_exit() {
    # In local detached mode, we want the services to keep running after the script exits.
    # The trap will still run, but we'll just print a message and return.
    if $NO_DOCKER && $DETACH; then
        echo "Detached mode: background services will continue to run."
        echo "To stop them later, run: ./start.sh --stop"
        return
    fi
    if [ -n "$COMPOSE_LOGS_PID" ]; then echo "Stopping background compose log tail (PID $COMPOSE_LOGS_PID)..." >&2; kill "$COMPOSE_LOGS_PID" 2>/dev/null || true; fi
    if [ -n "$PLAYWRIGHT_LOG_PID" ]; then echo "Stopping Playwright backend log tail (PID $PLAYWRIGHT_LOG_PID)..." >&2; kill "$PLAYWRIGHT_LOG_PID" 2>/dev/null || true; fi
    if [ -n "$BACKEND_LOG_TAIL_PID" ]; then echo "Stopping backend log tail (PID $BACKEND_LOG_TAIL_PID)..." >&2; kill "$BACKEND_LOG_TAIL_PID" 2>/dev/null || true; fi
    if [ -n "$BACKEND_PID" ]; then echo "Stopping local backend (PID $BACKEND_PID)..." >&2; kill "$BACKEND_PID" 2>/dev/null || true; fi
    if [ -n "$FRONTEND_PID" ]; then echo "Stopping local frontend (PID $FRONTEND_PID)..." >&2; kill "$FRONTEND_PID" 2>/dev/null || true; fi
}

# Register the cleanup function to run on EXIT
trap _cleanup_on_exit EXIT

# attempt to free any known ports that might conflict with the
# docker-compose services. this is especially helpful when a stray
# development server (vite, flask, etc.) is still running and prevents
# containers from binding their expected ports. the list below mirrors the
# ports exposed in docker-compose.yml; add or remove entries as needed.
clear_ports() {
    # Helper to find all PIDs listening on a port for robust cleanup.
    _get_pids_on_port() {
        local port="${1:-}"
        local pids=""

        if command -v fuser >/dev/null 2>&1; then
            # Linux-specific, very reliable. Returns space-separated PIDs.
            pids=$(fuser -n tcp "$port" 2>/dev/null | tr -s ' ' '\n' || true)
        elif command -v lsof >/dev/null 2>&1; then
            # macOS/Linux. Returns one PID per line.
            pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
        elif command -v netstat >/dev/null 2>&1; then
            # Linux (netstat -tulpn) or Windows (netstat -ano)
            if netstat -tulpn >/dev/null 2>&1; then
                pids=$(netstat -tulpn 2>/dev/null | grep -E ":$port\b" | awk '{print $7}' | cut -d/ -f1 | sort -u || true)
            else
                # Windows-style netstat -ano
                pids=$(netstat -ano 2>/dev/null | grep -E ":$port\b" | awk '{print $NF}' | tr -d '\r' | sort -u || true)
            fi
        elif command -v ss >/dev/null 2>&1; then
            # Linux (ss -ltnp). Use grep with PCRE if available for robustness.
            if grep -oP 'pid=\K[0-9]+' <<<"" >/dev/null 2>&1; then
                pids=$(ss -ltnp 2>/dev/null | grep -E ":$port\b" | grep -oP 'pid=\K[0-9]+' | sort -u || true)
            else # Fallback for systems without grep -P (e.g., macOS)
                pids=$(ss -ltnp 2>/dev/null | grep -E ":$port\b" | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | sort -u || true)
            fi
        fi

        # Return a clean, newline-separated list of numeric PIDs
        echo "$pids" | grep '^[0-9]\+$' | sort -u
    }

    local ports=("$@")
    if [ ${#ports[@]} -eq 0 ]; then
        ports=(8000 8001 5173 6333)
    fi
    echo "Attempting to free ports: ${ports[*]}..."
    for p in "${ports[@]}"; do
        local pids_to_kill
        pids_to_kill=$(_get_pids_on_port "$p")
        if [ -n "$pids_to_kill" ]; then
            # Loop over each PID found for the port
            for pid in $pids_to_kill; do
                echo "  Found process $pid listening on port $p."
                if command -v taskkill >/dev/null 2>&1; then
                    echo "  Attempting to kill process $pid with taskkill /F..."
                    taskkill /PID "$pid" /F >/dev/null 2>&1 || true
                elif kill -0 "$pid" >/dev/null 2>&1; then
                    echo "  Attempting graceful kill of process $pid..."
                    kill "$pid" >/dev/null 2>&1 || true
                    sleep 0.5 # Give it a moment to terminate
                    if kill -0 "$pid" >/dev/null 2>&1; then
                        echo "  Process $pid still running, forcing kill -9..."
                        kill -9 "$pid" >/dev/null 2>&1 || true
                    fi
                else
                    echo "  Process $pid no longer exists; skipping kill."
                fi
            done

            # Verify if the port is actually free now
            if [ -n "$(_get_pids_on_port "$p")" ]; then
                echo "  Warning: Port $p is still in use after attempted kills." >&2
            else
                echo "  Port $p successfully freed."
            fi
        fi
    done
}

show_port_status() {
    ports=(8000 8001 5173 6333)
    echo "Inspecting port usage for known service ports (this may take a moment)..."
    for p in "${ports[@]}"; do
        echo "--- port $p ---"
        if command -v lsof >/dev/null 2>&1; then
            lsof -i tcp:"$p" -Pn || true
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -tulpn >/dev/null 2>&1; then
                netstat -tulpn 2>/dev/null | grep -E ":$p( |$)" || true
            else
                netstat -ano 2>/dev/null | grep -E ":$p( |$)" || true
            fi
        elif command -v ss >/dev/null 2>&1; then
            ss -ltnp 2>/dev/null | grep -E ":$p( |$)" || true
        else
            echo "Port inspection unavailable; install lsof, netstat or ss to diagnose port conflicts."
        fi
    done
}

clear_logs() {
    echo "Clearing previous log files..."
    echo "Resetting local logs"
    mkdir -p logs
    rm -f logs/backend.log logs/frontend.log logs/*.log || true
    rm -f start.log ngrok.log playwright_backend.log || true
}

cleanup_frontend_node_modules() {
    local node_modules_path="frontend/node_modules"
    if [ -d "$node_modules_path" ]; then
        echo "Cleaning stale frontend/node_modules... (using rimraf for cross-platform compatibility)" >&2
        # The 'rimraf' package is the industry standard for reliably deleting node_modules.
        # Using npx ensures it's available without a global install.
        # This is much simpler and more robust than the multi-tool approach.
        if command -v npx >/dev/null 2>&1; then
            npx --yes rimraf "$node_modules_path" 2>/dev/null || true
        else
            # Fallback for environments without npx
            echo "npx not found, falling back to 'rm -rf'. This may fail on Windows." >&2
            rm -rf "$node_modules_path" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ]; then
            echo "Warning: frontend/node_modules still exists after cleanup attempt. This can happen on Windows if a process (like a file watcher or editor) has a lock on a file inside the directory. Please close any related programs and try again." >&2
        fi
    fi
}

# verify prerequisites are available when Docker is required
# (Docker is not mandatory for --no-docker/--local mode.)

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
  --build-dist create a distributable zip file of the project and exit
  --diag     emit a small diagnostics log (docker info, ps, etc.)
  --ports    show which processes are using the service ports and exit
  --stop     gracefully stop all running services (docker and local) and exit
  --log      capture docker-compose service logs to start.log
  --clear    stop and remove running compose services (docker-compose down)
  --fresh    force clean startup (compose down + clear ports + full frontend reinstall)
  --pause    pause before startup and wait for Enter confirmation
  --input-flags  prompt for additional flags interactively before startup
  --frontend      start the React frontend dev server (npm run dev) and log output (default)
  --no-frontend   do not attempt to start the frontend service
  --no-ngrok      do not start ngrok tunnel even if ngrok is installed
    --docker-build    run `docker build` for the repository root Dockerfile
    --buildx          use `docker buildx build` (supports --platform)
    --push-image      push the built image to the configured registry (requires `--image-tag`)
    --image-tag=<name:tag>  override image tag used for build/push (default: concierge:latest)
    --platform=<list> comma-separated platforms for buildx (default: linux/amd64)
    --build-frontend        build frontend during Docker build (passes BUILD_FRONTEND=1)
    --install-full-reqs     install `requirements.full.txt` instead of `requirements.txt`
    --vite-api-url=<url>    pass VITE_API_URL build-arg into frontend build
    --no-docker, --local    start backend/frontend locally without Docker
  --no-browser-open       do not automatically open the browser after startup
  --verify                verify installation of all required dependencies and exit
  --restart               stop all services and then start them again
  --status                check the status of detached local services and exit
  --detach                in local mode, detach and leave services running in background
  -h, --help display this message
  --monitor               in local mode, tail the backend log to the console for real-time monitoring

Examples:
  start.sh --build-dist                  # build and package for distribution
  start.sh --ports                       # check for port conflicts
  start.sh --no-docker       start backend and frontend locally without Docker
  start.sh --local           same as --no-docker
  start.sh --prune --yes --build --diag  # full clean, build, and log then up
  start.sh                               # bring up compose services
  start.sh --clear                       # tear down compose services
  start.sh --build-dist                  # build and package for distribution
  start.sh --stop                        # stop all running services
USAGE
}

PRUNE=false
YES=false
BUILD=false
BUILD_DIST=false
DIAG=false
LOGS=false
PORTS=false
TEST=false
BUILD_DIST=false
STOP=false
# Docker image build/push flags
DOCKER_BUILD=false
PUSH_IMAGE=false
IMAGE_TAG="concierge:latest"
# Buildx support
DOCKER_BUILDX=false
PLATFORMS="linux/amd64"
BUILD_FRONTEND=false
INSTALL_FULL_REQUIREMENTS=false
VITE_API_URL_ARG=""
VITE_API_URL_DOCKER_ARG=""
# frontend will be started by default; use --no-frontend to skip
FRONTEND=true
# ngrok will be started automatically if available; use --no-ngrok to skip
NGROK=true
CLEAR=false
NO_DOCKER=false
VERIFY=false
FRESH=false
PAUSE=false
INPUT_FLAGS=false
NO_BROWSER_OPEN=false
NGROK_URL_SET=false
DETACH=false
MONITOR=false
RESTART=false

STATUS=false
apply_arg() {
    local arg="$1"
    case "$arg" in
        --build-dist) BUILD_DIST=true ;;
        --prune) PRUNE=true ;;
        --yes) YES=true ;;
        --build) BUILD=true ;;
        --diag) DIAG=true ;;
        --ports) PORTS=true ;;
        --stop) STOP=true ;;
        --log) LOGS=true ;;
        --test) TEST=true ;;
        --docker-build) DOCKER_BUILD=true ;;
        --buildx) DOCKER_BUILDX=true ;;
        --push-image) PUSH_IMAGE=true ;;
        --image-tag=*) IMAGE_TAG="${arg#--image-tag=}" ;;
        --platform=*) PLATFORMS="${arg#--platform=}" ;;
        --build-frontend) BUILD_FRONTEND=true ;;
        --install-full-reqs) INSTALL_FULL_REQUIREMENTS=true ;;
        --vite-api-url=*) VITE_API_URL_ARG="${arg#--vite-api-url=}" ;;
        --vite-api-url-docker=*) VITE_API_URL_DOCKER_ARG="${arg#--vite-api-url-docker=}" ;;
        --frontend) FRONTEND=true ;;  # explicit enable (redundant)
        --no-frontend) FRONTEND=false ;;
        --no-ngrok) NGROK=false ;;
        --clear) CLEAR=true ;;
        --no-browser-open) NO_BROWSER_OPEN=true ;;
        --verify) VERIFY=true ;;
        --fresh) FRESH=true ;;
        --pause) PAUSE=true ;;
        --input-flags) INPUT_FLAGS=true ;;
        --no-docker|--local) NO_DOCKER=true ;;
        --monitor) MONITOR=true ;;
        --restart) RESTART=true ;;
        --detach) DETACH=true ;;
        --status) STATUS=true ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            print_usage
            exit 1
            ;;
    esac
}

for arg in "$@"; do
    apply_arg "$arg"
done

if $INPUT_FLAGS; then
    echo "Enter additional startup flags (space-separated), or press Enter to continue:"
    read -r extra_flags_line || true
    if [ -n "${extra_flags_line:-}" ]; then
        # shellcheck disable=SC2206
        extra_flags=( $extra_flags_line )
        for arg in ${extra_flags[@]+"${extra_flags[@]}"}; do
            apply_arg "$arg"
        done
    fi
fi

echo "Startup flags:"
echo "  PRUNE=${PRUNE} YES=${YES} BUILD=${BUILD} BUILD_DIST=${BUILD_DIST} DIAG=${DIAG} PORTS=${PORTS} LOGS=${LOGS} TEST=${TEST} STOP=${STOP}"
echo "  FRONTEND=${FRONTEND} NGROK=${NGROK} CLEAR=${CLEAR} FRESH=${FRESH} NO_DOCKER=${NO_DOCKER} MONITOR=${MONITOR}"
echo "  DETACH=${DETACH} STATUS=${STATUS}"
echo "  RESTART=${RESTART}"
echo "  NO_BROWSER_OPEN=${NO_BROWSER_OPEN}"
echo "  DOCKER_BUILD=${DOCKER_BUILD} DOCKER_BUILDX=${DOCKER_BUILDX} PUSH_IMAGE=${PUSH_IMAGE}"
echo "  IMAGE_TAG=${IMAGE_TAG} PLATFORMS=${PLATFORMS}"
if [ -n "${VITE_API_URL_ARG:-}" ]; then
    echo "  VITE_API_URL_ARG=${VITE_API_URL_ARG}"
fi
if [ -n "${VITE_API_URL_DOCKER_ARG:-}" ]; then
    echo "  VITE_API_URL_DOCKER_ARG=${VITE_API_URL_DOCKER_ARG}"
fi

if $DETACH && ! $NO_DOCKER; then
    echo "Warning: --detach is only applicable in --no-docker (local) mode. Ignoring --detach." >&2
    DETACH=false
fi

if $NO_DOCKER && $BUILD; then
    echo "Warning: The --build flag is for Docker mode and has no effect with --no-docker or --local. Ignoring --build." >&2
    BUILD=false
fi

# --- Major Operation Functions ---

do_prune() {
    if confirm "Prune docker system (containers/images/networks/volumes)?"; then
        echo "Pruning docker system..."
        docker system prune -af || echo "prune failed, continuing" >&2
    else
        echo "Skipping prune."
    fi
}

do_build_dist() {
    echo "--- Building Distribution Package ---"
    # This function handles the --build-dist flag.
    echo "Step 1: Creating distribution zip package (concierge-dist.zip) using 'git archive'..."
    # Using 'git archive' is cleaner and automatically respects .gitignore.
    # It creates an archive of the files tracked by Git.
    # The output file is specified with --output. HEAD refers to the latest commit.
    if git archive --format=zip --output=concierge-dist.zip HEAD; then
        echo "concierge-dist.zip created successfully."
    else
        die "Failed to create distribution package with 'git archive'. Make sure you are in a git repository and have committed your files."
    fi
    exit 0
}

do_teardown() {
    echo "--- Teardown Phase ---"
    if ! $NO_DOCKER; then
        if $FRESH; then
            echo "Stopping and removing containers and volumes via 'compose down -v'..."
            compose down -v || true # Don't die if it fails, might not be running
        elif $CLEAR; then
            echo "Stopping and removing containers via 'compose down'..."
            compose down || true
        elif $STOP; then
            echo "Stopping containers via 'compose stop'..."
            compose stop || true
        fi
    fi

    # Also stop any detached local services by reading their PID files.
    # This ensures that `./start.sh --stop` cleans up everything.
    local backend_pid_file="logs/backend.pid"
    if [ -f "$backend_pid_file" ]; then
        local backend_pid
        backend_pid=$(cat "$backend_pid_file")
        if [ -n "$backend_pid" ] && kill -0 "$backend_pid" >/dev/null 2>&1; then
            echo "Stopping detached local backend (PID: $backend_pid)..."
            kill "$backend_pid" 2>/dev/null || true
        fi
        rm -f "$backend_pid_file"
    fi
    local frontend_pid_file="logs/frontend.pid"
    if [ -f "$frontend_pid_file" ]; then
        local frontend_pid
        frontend_pid=$(cat "$frontend_pid_file")
        if [ -n "$frontend_pid" ] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
            echo "Stopping detached local frontend (PID: $frontend_pid)..."
            kill "$frontend_pid" 2>/dev/null || true
        fi
        rm -f "$frontend_pid_file"
    fi
    echo "Stopping any processes on known ports..."
    clear_ports
    if pgrep -f 'ngrok http 8000' >/dev/null 2>&1; then
        echo "Stopping ngrok process..."
        pkill -f 'ngrok http 8000' || true
    fi
    if $FRESH; then
        clear_logs
    fi
    echo "--- Teardown Complete ---"
}

do_verify() {
    echo "--- Verifying System Dependencies ---"
    local all_good=true

    echo "Checking Docker..."
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        echo "  [OK] Docker is installed and running."
    else
        echo "  [FAIL] Docker is not installed or not running."
        all_good=false
    fi

    echo "Checking Docker Compose..."
    if compose version >/dev/null 2>&1; then
        echo "  [OK] Docker Compose is available."
    else
        echo "  [FAIL] Docker Compose is not available."
        all_good=false
    fi

    echo "Checking Node.js..."
    if command -v node >/dev/null 2>&1; then
        echo "  [OK] Node.js is installed ($(node -v))."
    else
        echo "  [FAIL] Node.js is not installed."
        if $NO_DOCKER; then all_good=false; else echo "  [WARN] Local Node not required when using Docker."; fi
    fi

    echo "Checking npm..."
    if command -v npm >/dev/null 2>&1; then
        echo "  [OK] npm is installed ($(npm -v))."
    else
        echo "  [FAIL] npm is not installed."
        if $NO_DOCKER; then all_good=false; fi
    fi

    echo "Checking Python..."
    local py
    if py=$(find_python); then
        echo "  [OK] Python is installed ($($py --version 2>&1))."

        echo "Checking Python packages from requirements.txt..."
        if [ -f "requirements.txt" ]; then
            local missing_pkgs=()
            # Read requirements.txt, ignore comments/empty lines, and extract package names.
            while IFS= read -r line || [[ -n "$line" ]]; do
                line=$(echo "$line" | sed 's/#.*//' | xargs) # strip comments and whitespace
                if [ -z "$line" ]; then continue; fi

                # Extract package name (e.g., "fastapi" from "fastapi>=0.95.0")
                local pkg_name
                pkg_name=$(echo "$line" | sed -E 's/([a-zA-Z0-9\._-]+).*/\1/')

                # Check if pip can show the package, which means it's installed.
                if ! "$py" -m pip show "$pkg_name" >/dev/null 2>&1; then
                    missing_pkgs+=("$pkg_name")
                fi
            done < "requirements.txt"

            if [ ${#missing_pkgs[@]} -eq 0 ]; then
                echo "  [OK] All packages from requirements.txt are installed."
                # Now, check for dependency conflicts among installed packages.
                if ! "$py" -m pip check >/dev/null 2>&1; then
                    echo "  [WARN] Python environment has dependency conflicts. Run '$py -m pip check' for details."
                    if $NO_DOCKER; then all_good=false; fi
                else
                    echo "  [OK] All Python package dependencies are satisfied."
                fi
            else
                echo "  [WARN] Missing Python packages from requirements.txt: ${missing_pkgs[*]}"
                if $NO_DOCKER; then
                    local req_file_to_install="requirements.txt"
                    if [ -f "requirements.full.txt" ]; then
                        echo "  [INFO] Full requirements file found, will use requirements.full.txt for local setup."
                        req_file_to_install="requirements.full.txt"
                    fi
                    echo "  [AUTO-FIX] Attempting to install from ${req_file_to_install}..."
                    "$py" -m pip install -r "${req_file_to_install}" > logs/pip_verify_install.log 2>&1 || echo "  [FAIL] Auto-install failed. Run: $py -m pip install -r ${req_file_to_install}"
                fi
                all_good=false
            fi
        else
            echo "  [WARN] requirements.txt not found. Cannot verify Python packages."
            if $NO_DOCKER; then all_good=false; fi
        fi
    else
        echo "  [FAIL] Python 3 is not installed."
        if $NO_DOCKER; then all_good=false; else echo "  [WARN] Local Python not required when using Docker."; fi
    fi

    echo "--- Verification Complete ---"
    if $all_good; then
        echo "All required system dependencies are present!"
        exit 0
    else
        echo "Some system dependencies are missing. Please install them and try again."
        exit 1
    fi
}

do_status() {
    if ! $NO_DOCKER; then
        echo "--- Checking Status of Docker Services ---"
        if command -v docker >/dev/null 2>&1; then
            docker ps --filter "name=quesarc_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  No Concierge containers found."
        else
            echo "  Docker not found."
        fi
    fi
    echo "--- Checking Status of Local Detached Services (Background) ---"
    local backend_running=false

    # Check backend
    local backend_pid_file="logs/backend.pid"
    if [ -f "$backend_pid_file" ]; then
        local backend_pid
        backend_pid=$(cat "$backend_pid_file")
        if [ -n "$backend_pid" ] && kill -0 "$backend_pid" >/dev/null 2>&1; then
            echo "  [RUNNING] Backend (PID: $backend_pid) is running."
            backend_running=true
        else
            echo "  [STOPPED] Backend is not running (or PID file is stale)."
        fi
    else
        echo "  [STOPPED] Backend is not running (PID file not found)."
    fi

    # Check frontend
    local frontend_pid_file="logs/frontend.pid"
    if [ -f "$frontend_pid_file" ]; then
        local frontend_pid
        frontend_pid=$(cat "$frontend_pid_file")
        if [ -n "$frontend_pid" ] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
            echo "  [RUNNING] Frontend (PID: $frontend_pid) is running."
        else
            echo "  [STOPPED] Frontend is not running (or PID file is stale)."
        fi
    else
        # This is not an error, as frontend is optional.
        echo "  [INFO] Frontend PID file not found (may not have been started)."
    fi

    echo "--- Status Check Complete ---"
}

do_diag() {
    echo "Writing diagnostics to start.log"
    {
        echo "--- docker version ---"
        docker version || true
        echo
        echo "--- docker-compose version ---"
        compose version || true
        echo
        echo "--- docker ps -a ---"
        docker ps -a || true
        echo "--- end diagnostics ---"
    } | tee start.log
}

do_docker_build() {
    local detected_image=""
    local detected_container=""
    local build_dockerfile=""
    local build_context=""

    # Auto-detect image tag and Dockerfile/context from compose or repo layout
    if [ -f "docker-compose.yml" ]; then
        echo "Parsing docker-compose.yml to infer build settings..."
        # extract the 'app' service block (lines indented under 'app:')
        svc_block=$(awk '/^\s*app:\s*$/{flag=1;next}/^[^[:space:]]/{flag=0}flag{print}' docker-compose.yml || true)
        # look for explicit image: or container_name: fields
        detected_image=$(echo "$svc_block" | sed -n 's/^[[:space:]]*image:[[:space:]]*//p' | tr -d '"' | tr -d "'" | xargs || true)
        detected_container=$(echo "$svc_block" | sed -n 's/^[[:space:]]*container_name:[[:space:]]*//p' | tr -d '"' | tr -d "'" | xargs || true)
        if [ -n "$detected_image" ] && [ "$IMAGE_TAG" = "concierge:latest" ]; then
            IMAGE_TAG="$detected_image"
        elif [ -n "$detected_container" ] && [ "$IMAGE_TAG" = "concierge:latest" ]; then
            IMAGE_TAG="$detected_container"
        fi
        # if build context specified with a Dockerfile path, prefer that (simple heuristics)
        build_dockerfile=$(echo "$svc_block" | sed -n 's/^[[:space:]]*dockerfile:[[:space:]]*//p' | tr -d '"' | tr -d "'" | xargs || true)
        build_context=$(echo "$svc_block" | sed -n 's/^[[:space:]]*build:[[:space:]]*//p' | tr -d '"' | tr -d "'" | xargs || true)
    fi

    # Fallback: search for common Dockerfile locations
    DOCKERFILE_PATH=""
    if [ -f Dockerfile ]; then
        DOCKERFILE_PATH="Dockerfile"
    elif [ -f app/Dockerfile ]; then
        DOCKERFILE_PATH="app/Dockerfile"
    elif [ -f frontend/Dockerfile ]; then
        DOCKERFILE_PATH="frontend/Dockerfile"
    elif [ -n "$build_dockerfile" ]; then
        DOCKERFILE_PATH="$build_dockerfile"
    fi

    # If IMAGE_TAG is still the default, derive from repo directory name
    if [ "$IMAGE_TAG" = "concierge:latest" ]; then
        repo_name=$(basename "$(pwd)")
        IMAGE_TAG="${repo_name}:latest"
    fi

    echo "Using image tag: ${IMAGE_TAG}"
    if [ -n "$DOCKERFILE_PATH" ]; then
        echo "Detected Dockerfile: ${DOCKERFILE_PATH}"
    else
        echo "No Dockerfile explicitly detected; building from repository root context"
    fi

    if confirm "Build Docker image ${IMAGE_TAG}?"; then
        echo "Building Docker image ${IMAGE_TAG} from repository root..."
        if $DOCKER_BUILDX; then
            # ensure buildx is available
            if ! docker buildx version >/dev/null 2>&1; then
                echo "docker buildx not available; attempting to continue with standard docker build" >&2
                docker build -t "${IMAGE_TAG}" . || die "docker build failed"
            else
                # ensure a builder is selected
                BUILDER_NAME="concierge-builder"
                if ! docker buildx inspect "${BUILDER_NAME}" >/dev/null 2>&1; then
                    echo "Creating buildx builder ${BUILDER_NAME}..."
                    docker buildx create --name "${BUILDER_NAME}" --use || die "failed to create buildx builder"
                else
                    docker buildx use "${BUILDER_NAME}" || true
                fi

                # assemble build-arg flags for both buildx and docker build
                BUILD_ARGS=()
                if $BUILD_FRONTEND; then
                    BUILD_ARGS+=(--build-arg "BUILD_FRONTEND=1")
                fi
                if $INSTALL_FULL_REQUIREMENTS; then
                    BUILD_ARGS+=(--build-arg "INSTALL_FULL_REQUIREMENTS=1")
                fi
                if [ -n "$VITE_API_URL_ARG" ]; then
                    BUILD_ARGS+=(--build-arg "VITE_API_URL=${VITE_API_URL_ARG}")
                fi
                if [ -n "$VITE_API_URL_DOCKER_ARG" ]; then
                    BUILD_ARGS+=(--build-arg "VITE_API_URL_DOCKER=${VITE_API_URL_DOCKER_ARG}")
                fi

                # decide push/load flags: --push required for multi-platform
                if $PUSH_IMAGE; then
                    BUILDX_FLAGS=(--platform "${PLATFORMS}" --tag "${IMAGE_TAG}" --push)
                else
                    # try to load into local Docker if single-platform
                    if echo "${PLATFORMS}" | grep -q ','; then
                        echo "Multi-platform build without push cannot load into local Docker; the image will not be available locally." >&2
                        BUILDX_FLAGS=(--platform "${PLATFORMS}" --tag "${IMAGE_TAG}")
                    else
                        BUILDX_FLAGS=(--platform "${PLATFORMS}" --tag "${IMAGE_TAG}" --load)
                    fi
                fi
                docker buildx build "${BUILDX_FLAGS[@]}" ${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"} . || die "docker buildx build failed"
            fi
        else
            docker build -t "${IMAGE_TAG}" ${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"} . || die "docker build failed"
        fi

        echo "Built image ${IMAGE_TAG}";

        if $PUSH_IMAGE && ! $DOCKER_BUILDX; then
            if confirm "Push image ${IMAGE_TAG} to registry?"; then
                echo "Pushing image ${IMAGE_TAG}..."
                docker push "${IMAGE_TAG}" || die "docker push failed"
                echo "Pushed ${IMAGE_TAG}";
            else
                echo "Skipping push of ${IMAGE_TAG}."
            fi
        fi
    else
        echo "Skipping docker build."
    fi
}

get_frontend_port_from_log() {
    local log_file="logs/frontend.log"
    local timeout=30 # seconds to wait for the port
    local start_time
    start_time=$(date +%s)

    echo "Attempting to detect frontend port from log file: $log_file"
    echo "Parsing frontend log for port number..."
    while [ $(( $(date +%s) - start_time )) -lt "$timeout" ]; do
        if [ -f "$log_file" ]; then
            # Look for "Local: http://localhost:PORT/"
            local port_line
            port_line=$(grep 'Local:' "$log_file" | tail -n 1)
            if [ -n "$port_line" ]; then
                echo "Found 'Local:' line in log: $port_line"
                # Extract port number using a robust grep/cut combination that is less
                # sensitive to special characters or spacing in the log line.
                local port
                port=$(echo "$port_line" | grep -o 'localhost:[0-9]*' | cut -d: -f2)
                echo "Extracted port: $port"
                if [[ "$port" =~ ^[0-9]+$ ]]; then
                    echo "$port"
                    return 0
                fi
            fi
        fi
        sleep 1
        local elapsed_time=$(( $(date +%s) - start_time ))
        echo "Still waiting for frontend port (elapsed: ${elapsed_time}s)..."
    done
    return 1
}

do_start_local() {
    echo "Starting local services without Docker"
    clear_logs
    echo "Freeing known ports before local startup..."
    clear_ports
    if $FRONTEND; then
        write_frontend_env_for_local || true
    fi
    start_local_backend # Start the backend first
    if $MONITOR; then
        echo "Monitoring backend startup... (tail -f logs/backend.log)"
        # Give a moment for the log file to be created
        sleep 1
        tail -f logs/backend.log &
        BACKEND_LOG_TAIL_PID=$!
    fi
    if wait_for_backend 127.0.0.1 8000 120; then
        echo "Local backend ready."
    else
        echo "Warning: local backend did not become healthy on 127.0.0.1:8000 after first attempt." >&2
        if [ -n "${BACKEND_PID:-}" ]; then
            echo "Stopping backend PID ${BACKEND_PID} and retrying..."
            kill -9 "${BACKEND_PID}" >/dev/null 2>&1 || true
        fi
        clear_ports

        echo "Attempting self-healing: Re-installing local dependencies..."
        local py
        local req_file="requirements.txt"
        if [ -f "requirements.full.txt" ]; then
            req_file="requirements.full.txt"
        fi

        if py=$(find_python); then
            echo "Running pip install on ${req_file} for self-healing..."
            if ! "$py" -m pip install -r "${req_file}" > logs/pip_install.log 2>&1; then
                echo "  [FAIL] Auto-install failed. See logs/pip_install.log for details." >&2
                echo "  Last 10 lines of pip_install.log:" >&2
                tail -n 10 logs/pip_install.log >&2
            fi
        fi

        start_local_backend
        if wait_for_backend 127.0.0.1 8000 120; then
            echo "Local backend ready after retry."
        else
            echo "Error: local backend still did not become healthy on 127.0.0.1:8000 after retry." >&2
            show_port_status
            echo "--- tail of backend log ---" >&2
            tail -n 40 logs/backend.log >&2 || true
            echo "Check logs/backend.log for details on backend startup failure." >&2
            die "Local startup failed because the backend could not bind and become ready."
        fi
    fi
    if $FRONTEND; then
        echo "Starting local frontend..."
        start_local_frontend
        if wait_for_frontend 127.0.0.1 "$FRONTEND_PORT" 120; then
            echo "Local frontend ready."
        else
            echo "Warning: local frontend did not become healthy on 127.0.0.1:$FRONTEND_PORT after first attempt." >&2
            if [ -n "${FRONTEND_PID:-}" ]; then
                echo "Stopping frontend PID ${FRONTEND_PID} and retrying..."
                kill -9 "${FRONTEND_PID}" >/dev/null 2>&1 || true
            fi
            clear_ports "$FRONTEND_PORT"

            echo "Attempting self-healing: Re-installing local frontend dependencies..."
            cleanup_frontend_node_modules
            if ! npm --prefix frontend install --no-audit --no-fund > logs/npm_install_frontend.log 2>&1; then
                echo "  [FAIL] Frontend npm install failed. See logs/npm_install_frontend.log for details." >&2
                echo "  Last 10 lines of npm_install_frontend.log:" >&2
                tail -n 10 logs/npm_install_frontend.log >&2
            fi

            start_local_frontend
            if wait_for_frontend 127.0.0.1 "$FRONTEND_PORT" 90; then
                echo "Local frontend ready after retry."
            else
                echo "Error: local frontend still did not become healthy on 127.0.0.1:$FRONTEND_PORT after retry." >&2
                show_port_status
                echo "--- tail of frontend log ---" >&2
                tail -n 40 logs/frontend.log >&2 || true
                die "Local startup failed because the frontend could not bind and become ready."
            fi
        fi
    fi
    # After all services are confirmed healthy, open the browser.
    if ! $NO_BROWSER_OPEN && $FRONTEND; then
        echo "Opening browser to frontend..."
        open_browser "http://localhost:$FRONTEND_PORT"
    elif $FRONTEND; then
        # This branch is hit if the frontend is enabled but browser opening is not.
        echo "Browser auto-open is disabled (due to --no-browser-open or other settings)."
    fi
    echo "Local startup process complete."
}

do_start_docker() {
    # If --clear or --fresh was passed, main() has already run do_teardown.
    # Otherwise, we run 'compose down' here to ensure a clean state and prevent container name conflicts.
    if ! $CLEAR && ! $FRESH; then
        echo "--- Ensuring Clean State ---"
        echo "Stopping and removing any existing Docker services to prevent conflicts..."
        compose down || true
        clear_ports
    fi

    echo "--- Building/Updating Docker Image for 'app' service ---"
    # Always build the 'app' service. Docker's cache makes this fast if no files have changed.
    # This prevents 'pull access denied' errors for the local image used by worker/flower.
    compose build app || die "compose build failed"

    echo "Clearing stale Python bytecode to prevent startup cache issues..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    local services_to_start=("app" "worker" "flower" "redis" "chroma" "qdrant")
    if $FRONTEND; then services_to_start+=("frontend"); fi
    echo "--- Starting Docker Services (${services_to_start[*]}) ---"
    compose up -d "${services_to_start[@]}" || die "compose up failed"

    if $LOGS; then
        echo "Capturing docker-compose logs to start.log in background..."
        local services_to_log=("app")
        if $FRONTEND; then
            services_to_log+=("frontend")
        fi
        compose logs -f --no-color "${services_to_log[@]}" > start.log 2>&1 &
        COMPOSE_LOGS_PID=$!
        echo "Background log tail started with PID $COMPOSE_LOGS_PID."
        echo "You can view live logs by running: tail -f start.log"
    fi

    echo "--- Waiting for Backend ---"
    if wait_for_backend 127.0.0.1 8000 120; then
        echo "Backend ready; starting ngrok."
    else
        _recover_docker_backend
    fi
    if $TEST && ! wait_for_backend 127.0.0.1 8000 1; then
        die "Aborting test run because backend is not healthy on port 8000."
    fi
    echo "--- Starting Ngrok ---"
    start_ngrok

    if $FRONTEND; then
        # The `compose up -d` command earlier already started all services, including the frontend.
        # The frontend container is responsible for its own dependency installation via `npm ci`.
        # We just need to ensure its environment is correct and wait for it to become healthy.
        if ! $NGROK_URL_SET; then
            write_frontend_env_for_docker || true
        fi
        echo "--- Waiting for Frontend ---"
        if wait_for_frontend 127.0.0.1 5173 90; then
            echo "Frontend container ready."
        else
            _recover_docker_frontend
        fi
        # check status and show logs if any container exited unexpectedly
        for svc in app frontend; do
            # use docker ps filter to reliably detect exited containers by name
            if docker ps -a --filter "name=quesarc_${svc}" --filter "status=exited" --format '{{.Names}}' | grep -q .; then
                echo "${svc^} container exited; here are the last 20 lines of its log:" >&2
                compose logs $svc --tail=20 >&2
            fi
        done
    fi

    # After all services are confirmed healthy, open the browser.
    if ! $NO_BROWSER_OPEN && $FRONTEND; then
        open_browser "http://localhost:5173"
    elif $FRONTEND; then
        # This branch is hit if the frontend is enabled but browser opening is not.
        echo "Browser auto-open is disabled (due to --no-browser-open or other settings)."
    fi
}

do_test() {
    echo "--test flag detected: launching Playwright suite and capturing logs"
    # Tail backend logs specifically for Playwright
    docker logs -f quesarc_app --since 1s > playwright_backend.log 2>&1 &
    PLAYWRIGHT_LOG_PID=$!
    echo "Playwright backend log tail started with PID $PLAYWRIGHT_LOG_PID."
    echo "You can view live Playwright backend logs by running: tail -f playwright_backend.log"
    # run tests from the embedded frontend directory; allow custom args via TEST_ARGS
    (cd frontend && npx playwright test ${TEST_ARGS:-})
    # The trap will handle killing PLAYWRIGHT_LOG_PID
    echo "Playwright run complete; backend log written to playwright_backend.log"
}

confirm() {
    local prompt="$1"
    if $YES; then
        return 0
    fi
    read -r -p "$prompt [y/N] " response || true
    case "$response" in
        [Yy]*) return 0 ;; 
        *) return 1 ;;
    esac
}

# Generic function to wait for a web service to become available
_wait_for_service() {
    local service_name="$1"
    local host="$2"
    local port="$3"
    local timeout="$4"
    local health_path="$5"
    local expected_text="${6:-}" # New parameter for expected text

    local start_time
    start_time=$(date +%s)
    local last_log_time=$start_time

    # Calculate a dynamic log interval based on the timeout.
    # We'll log progress roughly every 10% of the timeout,
    # but no more often than every 10s and no less often than every 30s.
    local log_interval=$(( timeout / 10 ))
    if (( log_interval < 10 )); then log_interval=10; fi
    if (( log_interval > 30 )); then log_interval=30; fi

    if ! command -v curl >/dev/null 2>&1; then
        die "Error: 'curl' is required for health checks, but it's not installed. Please install curl and try again."
    fi

    echo -n "Waiting for ${service_name} to become available on ${host}:${port} (timeout: ${timeout}s) "
    while [ $(( $(date +%s) - start_time )) -lt "$timeout" ]; do
        local curl_cmd="curl -fs --max-time 5 http://${host}:${port}${health_path}"
        local curl_output=""
        if [ -n "$expected_text" ]; then
            if curl_output=$($curl_cmd 2>/dev/null) && echo "$curl_output" | grep -qF -- "$expected_text"; then
                local elapsed=$(( $(date +%s) - start_time ))
                echo "" # newline
                echo "${service_name^} is available after ${elapsed}s. Health check succeeded at endpoint: ${health_path} (found text: '${expected_text}')"
                return 0
            fi
        else
            if $curl_cmd >/dev/null 2>&1; then # Just check for 200 status code
                local elapsed=$(( $(date +%s) - start_time ))
                echo "" # newline
                echo "${service_name^} is available after ${elapsed}s. Health check succeeded at endpoint: ${health_path}"
                return 0
            fi
        fi
        echo -n "." # Show progress

        local current_time=$(date +%s)
        if (( current_time - last_log_time >= log_interval )); then
            local elapsed=$(( current_time - start_time ))
            echo " (${elapsed}s)"
            echo -n "Waiting for ${service_name} to become available on ${host}:${port} (timeout: ${timeout}s) "
            last_log_time=$current_time
        fi

        sleep 1
    done

    echo "" # newline
    echo "Warning: ${service_name} did not become available on ${host}:${port}${health_path} after ${timeout}s." >&2
    echo "  Last curl attempt: $curl_cmd" >&2
    if [ -n "$expected_text" ]; then
        echo "  Expected text: '$expected_text'" >&2
        echo "  Last curl output (truncated):" >&2
        echo "$curl_output" | head -n 10 >&2
    fi
    return 1
}

wait_for_backend() {
    local host=${1:-127.0.0.1} # Default host
    local port=${2:-8000} # Default port is now 8000
    local timeout=${3:-30}
    # Use the specific readiness endpoint. This endpoint returns a 503 until
    # all startup components are initialized, which is the correct signal for readiness.
    _wait_for_service "backend" "$host" "$port" "$timeout" "/health/ready"
}

wait_for_frontend() {
    local host=${1:-127.0.0.1} # Default host
    local port=${2:-5173} # Increased timeout for more robust startup
    local timeout=${3:-30}
    # Check for a unique string from the homepage to ensure the app has rendered, not just the Vite server.
    _wait_for_service "frontend" "$host" "$port" "$timeout" "/" "Concierge"
}

get_ngrok_public_url() {
	local attempt=0
	local url=""
	local py

	# Find python once
	py=$(find_python) || true

	while [ "$attempt" -lt 10 ]; do
		if command -v curl >/dev/null 2>&1; then
			# Try to get the tunnels info from the ngrok agent API
			local body
            body=$(curl -s --max-time 2 http://127.0.0.1:4040/api/tunnels || true)

			if [ -n "$body" ] && [ -n "$py" ]; then
				# Use python to parse the JSON and extract the public_url
				url=$("$py" -c "import json,sys; data=json.load(sys.stdin); tunnels=data.get('tunnels', []); print(next((t.get('public_url') for t in tunnels if t.get('proto') == 'https'), ''))" <<<"$body" || true)
				if [ -n "$url" ]; then
					echo "$url"
					return 0
				fi
			fi
		fi
		sleep 2
		attempt=$((attempt + 1))
	done

	echo "Warning: ngrok public URL not detected after multiple attempts." >&2
	return 1
}

_recover_docker_backend() {
    echo "" >&2
    echo "--- BACKEND RECOVERY ---" >&2
    echo "The backend service failed to become healthy on http://127.0.0.1:8000." >&2
    echo "Showing last 50 lines of logs for the 'app' container:" >&2
    compose logs --tail=50 app >&2
    
    if confirm "Attempt to restart the 'app' container?"; then
        echo "Restarting 'app' container..."
        compose restart app
        echo "Waiting again for backend to become healthy on port 8000..."
        if wait_for_backend 127.0.0.1 8000 60; then
             echo "Backend is now healthy after restart."
             return 0
        fi
    fi

    echo "---" >&2
    echo "Error: Backend recovery failed. The service is still not responding on port 8000." >&2
    echo "Common issues:" >&2
    echo "1. Port Conflict: Another application might be using port 8000. Run './start.sh --ports' to check." >&2
    echo "2. Build Error: The Docker image may have failed to build correctly. Try running with '--build'." >&2
    echo "3. Dependency Issue: A service like Redis, Chroma, or Qdrant might not be running correctly." >&2
    echo "4. Code Error: There might be a syntax error or unhandled exception on backend startup." >&2
    die "Startup failed due to unresponsive backend service."
}

_recover_docker_frontend() {
    echo "" >&2
    echo "--- FRONTEND RECOVERY ---" >&2
    echo "The frontend service failed to become healthy on http://127.0.0.1:5173." >&2
    echo "Showing last 50 lines of logs for the 'frontend' container:" >&2
    compose logs --tail=50 frontend >&2

    if confirm "Attempt to restart the 'frontend' container?"; then
        echo "Restarting 'frontend' container..."
        compose restart frontend
        echo "Waiting again for frontend to become healthy..."
        if wait_for_frontend 127.0.0.1 5173 60; then
             echo "Frontend is now healthy after restart."
             return 0
        fi
    fi

    echo "---" >&2
    echo "Error: Frontend recovery failed. The service is still not responding." >&2
    echo "Common issues:" >&2
    echo "1. Port Conflict: Another application might be using port 5173. Run './start.sh --ports' to check." >&2
    echo "2. Build Error: The node image may have issues, or npm install failed inside the container." >&2
    echo "3. Backend Unavailability: The frontend may be failing because it cannot connect to the backend API." >&2
    die "Startup failed due to unresponsive frontend service."
}

find_python() {
	local candidate
	for candidate in "${VIRTUAL_ENV:-}/bin/python" "./.venv/bin/python" "./venv/bin/python" "./.venv/Scripts/python.exe" python3 python py; do
		if [ -z "$candidate" ]; then continue; fi
		if [ "$candidate" != "py" ] && ! command -v "$candidate" >/dev/null 2>&1 && [ ! -x "$candidate" ]; then
			continue
		fi
		if [ "$candidate" = "py" ]; then
			if py -3 -c 'import sys' >/dev/null 2>&1; then
				printf '%s' "py -3"
				return 0
			fi
		else
			if "$candidate" -c 'import sys' >/dev/null 2>&1; then
				printf '%s' "$candidate"
				return 0
			fi
		fi
	done
	return 1
}

_update_frontend_env() {
    local env_file="${1:-}"
    shift
    local tmp_file
    tmp_file=$(mktemp)
    touch "$env_file"
    local keys_to_set=()
    for arg in "$@"; do
        keys_to_set+=("$(echo "$arg" | cut -d= -f1)")
    done
    local pattern=$(printf "^(%s)=" "$(IFS=\|; echo "${keys_to_set[*]}")")
    grep -vE "$pattern" "$env_file" > "$tmp_file" 2>/dev/null || true
    for arg in "$@"; do
        echo "$arg" >> "$tmp_file"
    done
    mv "$tmp_file" "$env_file"
}

write_frontend_env() {
    local ngrok_url="${1:-}"
    local env_file="frontend/.env.local"
    if [ -z "$ngrok_url" ]; then return 1; fi
    _update_frontend_env "$env_file" \
        "VITE_API_URL=${ngrok_url}" \
        "BACKEND_URL=${ngrok_url}" \
        "VITE_API_URL_SET=ngrok" \
        "VITE_API_URL_AUTO_DETECT=true"
    echo "Written frontend environment file: ${env_file}"
}

write_frontend_env_for_local() {
    local env_file="frontend/.env.local"
    _update_frontend_env "$env_file" \
        'VITE_API_URL=http://127.0.0.1:8000' \
        'BACKEND_URL=http://127.0.0.1:8000' \
        'VITE_API_URL_SET=local-no-docker' \
        'VITE_API_URL_AUTO_DETECT=false'
    echo "Written local frontend environment file: ${env_file}"
    echo "  VITE_API_URL=http://127.0.0.1:8000"
    echo "  VITE_API_URL_SET=local-no-docker"
    return 0
}

write_frontend_env_for_docker() {
    local env_file="frontend/.env.local"
    _update_frontend_env "$env_file" \
        'VITE_API_URL=http://127.0.0.1:8000' \
        'BACKEND_URL=http://127.0.0.1:8000' \
        'VITE_API_URL_SET=docker-host' \
        'VITE_API_URL_AUTO_DETECT=false'
    echo "Written docker frontend environment file: ${env_file}"
    echo "  VITE_API_URL=http://127.0.0.1:8000"
    echo "  VITE_API_URL_SET=docker-host"
    return 0
}

start_local_backend() {
    local py
    py=$(find_python) || die "Python 3 is required for local backend startup"
    echo "Using Python executable: $py"
    
    local -a py_cmd
    if [[ "$py" == "py -3" ]]; then
        py_cmd=(py -3)
    else
        py_cmd=("$py")
    fi
    
    mkdir -p logs
    # For local mode, explicitly disable external vector DB and Celery broker
    # to prevent connection attempts and warnings.
    export VECTOR_DB="none"
    export CELERY_BROKER_URL="memory"
    export PORT=8000
    # Broaden the CORS list to handle Vite's automatic port incrementing (5173-5179).
    # This prevents 'Connection Refused' or CORS errors when the dashboard loads.
    local vite_ports="5173,5174,5175,5176,5177,5178,5179"
    export CORS_ALLOW_ORIGINS="http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001"
    for p in ${vite_ports//,/ }; do
        export CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS},http://localhost:$p,http://127.0.0.1:$p"
    done

    local -a backend_cmd
    if "${py_cmd[@]}" -m uvicorn --help >/dev/null 2>&1; then
        local uvicorn_opts=(--host 0.0.0.0 --port 8000 --reload --log-level trace)
        
        set -f # Disable globbing securely as tested in temp_bash_test.sh
        local reload_excludes=("frontend/node_modules/*" "**/node_modules/*" "frontend/*" ".*" "logs/*" "chroma_db/*" "qdrant_data/*")
        for exclude in "${reload_excludes[@]}"; do uvicorn_opts+=(--reload-exclude "$exclude"); done
        set +f # Re-enable globbing
        
        echo "Uvicorn command detected."
        backend_cmd=("${py_cmd[@]}" -u -m uvicorn "${uvicorn_opts[@]}" app:app)
    else
        die "Uvicorn not found. Please install it (e.g., 'pip install uvicorn')."
    fi
    echo "  (Logs will be in logs/backend.log)"
    "${backend_cmd[@]}" > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > logs/backend.pid
    sleep 2
}

start_local_frontend() {
    local node_modules_dir="frontend/node_modules"
    local package_lock="frontend/package-lock.json"
    local should_install=false
    if [ ! -d "$node_modules_dir" ]; then
        should_install=true
        echo "frontend/node_modules missing; installing dependencies"
    elif [ -f "$package_lock" ] && [ "$package_lock" -nt "$node_modules_dir" ]; then
        should_install=true
        echo "package-lock.json is newer than node_modules; reinstalling"
    fi
    if [ "$should_install" = true ]; then
        # Prefer 'npm ci' for deterministic installs from package-lock.json, mirroring Docker/CI.
        # Fall back to 'npm install' if the lock file is missing.
        if [ -f "$package_lock" ]; then
            echo "Using 'npm ci' for a clean, deterministic install..."
            npm --prefix frontend ci --no-audit --no-fund || die "npm ci failed"
        else
            echo "Warning: package-lock.json not found. Falling back to 'npm install'." >&2
            npm --prefix frontend install --no-audit --no-fund || die "npm install failed"
        fi
    else
        echo "frontend dependencies are up to date; skipping install"
    fi
    mkdir -p logs
    # Clear previous log to avoid parsing an old port number
    > logs/frontend.log
    # Use `npx vite` directly instead of `npm run dev` for better cross-platform
    # compatibility, especially on Windows where `npm run` might fail to find the executable.
    nohup npx --prefix frontend vite --host > logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > logs/frontend.pid
    echo "Local frontend started with PID ${FRONTEND_PID}; logs are in logs/frontend.log"

    # Detect the port from the log file
    local detected_port
    if detected_port=$(get_frontend_port_from_log); then
        FRONTEND_PORT="$detected_port"
        echo "Detected frontend running on port: $FRONTEND_PORT"
    else
        echo "Warning: Could not detect frontend port from logs. Will use default $FRONTEND_PORT." >&2
        # Reset to default if detection fails
        FRONTEND_PORT="5173"
    fi
}

frontend_needs_install() {
    local package_lock="frontend/package-lock.json"
    local node_modules_dir="frontend/node_modules"

    if [ ! -d "$node_modules_dir" ]; then
        return 0
    fi
    if [ -f "$package_lock" ] && [ "$package_lock" -nt "$node_modules_dir" ]; then
        return 0
    fi
    return 1
}

install_frontend_dependencies() {
    local force_reinstall="${1:-false}"
    if [ ! -d "frontend" ]; then
        echo "Warning: frontend directory not found, skipping dependency install." >&2
        FRONTEND=false # Disable frontend if directory doesn't exist
        return 0
    fi

    if [ "$force_reinstall" = "true" ]; then
        echo "Force-reinstall requested: cleaning frontend/node_modules"
        cleanup_frontend_node_modules
    fi

    if frontend_needs_install; then
        echo "Installing frontend dependencies..."
        npm --prefix frontend install --no-audit --no-fund || die "npm install failed"
    else
        echo "frontend dependencies are up to date; skipping install"
    fi
}

start_ngrok() {
    if ! $NGROK; then
        echo "Skipping ngrok startup (--no-ngrok specified)."
        return
    fi
    if ! command -v ngrok >/dev/null 2>&1; then
        echo "ngrok not found on PATH; skipping ngrok startup." >&2
        return
    fi
    if pgrep -f 'ngrok http 8000' >/dev/null 2>&1; then
        echo "ngrok tunnel already running for port 8000."
    else
        echo "Starting ngrok tunnel for backend on port 8000..."
        nohup ngrok http 8000 > ngrok.log 2>&1 &
        NGROK_PID=$!
        echo "ngrok started with PID ${NGROK_PID}; logs are in ngrok.log"
    fi

    local ngrok_url
    if ngrok_url=$(get_ngrok_public_url); then
        echo "Detected ngrok public URL: ${ngrok_url}"

        echo "Updating service registry with ngrok URL..."
        if command -v curl >/dev/null 2>&1; then
            # The backend is on localhost:8000
            curl -s -X POST --max-time 2 http://127.0.0.1:8000/api/v1/server/registry/update-url \
                 -H "Content-Type: application/json" \
                 -d "{\"url\": \"${ngrok_url}\"}" > /dev/null || echo "Warning: Failed to update service registry with ngrok URL." >&2
        else
            echo "Warning: curl not found, cannot update service registry." >&2
        fi

        if write_frontend_env "$ngrok_url"; then
            NGROK_URL_SET=true
        else
            echo "Warning: failed to write frontend env file." >&2
        fi
    else
        echo "Warning: could not detect ngrok public URL." >&2
    fi
}

main() {
    if $PAUSE; then
        echo "Startup paused. Press Enter to continue..."
        read -r _
    fi

    # --- Teardown Logic ---
    local IS_STARTUP_ACTION=false
    if $BUILD || $CLEAR || $FRESH || $LOGS || $TEST || $DIAG || $DOCKER_BUILD || $NO_DOCKER || $PRUNE; then
        IS_STARTUP_ACTION=true
    fi
    # A simple './start.sh' with no flags also implies startup.
    if [[ "$#" -eq 0 ]]; then
        IS_STARTUP_ACTION=true
    fi

    if $RESTART; then
        STOP=true
        IS_STARTUP_ACTION=true
    fi

    # --- Utility Actions ---
    if $STATUS; then do_status; if ! $IS_STARTUP_ACTION; then exit 0; fi; fi
    if $PORTS; then show_port_status; if ! $IS_STARTUP_ACTION; then exit 0; fi; fi
    if $BUILD_DIST; then do_build_dist; fi # This exits on its own

    if $FRESH; then
        echo "--fresh implies --clear, log clearing, and frontend reinstall."
        CLEAR=true
        if $FRONTEND; then
            echo "---fresh flag: ensuring a clean frontend install for local mode---"
            cleanup_frontend_node_modules
        fi
    fi

    if $STOP || $CLEAR || $FRESH; then
        do_teardown
    fi

    if $STOP && ! $IS_STARTUP_ACTION; then
        echo "Stop action complete. No other startup flags detected, so exiting."
        exit 0
    fi

    # --- Pre-Startup Actions ---
    if $PRUNE; then do_prune; fi
    if $VERIFY; then do_verify; fi
    if $DIAG; then do_diag; fi
    if $DOCKER_BUILD; then do_docker_build; fi

    # --- Main Startup Path ---
    echo "--- Starting Application ---"
    if $NO_DOCKER; then
        do_start_local
    else
        # Docker-based workflow
        if ! command -v docker >/dev/null 2>&1; then die "docker CLI not found; please install Docker"; fi
        if ! docker info >/dev/null 2>&1; then die "docker daemon not running or not accessible"; fi
        if ! compose version >/dev/null 2>&1; then die "docker compose not available (install docker-compose or use newer Docker)"; fi
        do_start_docker
    fi

    # --- Post-Startup Actions ---
    if $TEST; then
        do_test
    fi

    print_completion_urls
    echo "start.sh complete."

    if $NO_DOCKER && $MONITOR && ! $DETACH; then
        echo
        echo "Startup complete. Monitoring backend logs. Press Ctrl+C to stop all services."
        wait
    elif $FRONTEND; then
        # For any other mode (like --detach), provide a final, clear instruction.
        echo
        echo "To view the application, open this URL in your browser:"
        echo "  => http://localhost:${FRONTEND_PORT}"
    fi
}

main "$@"
