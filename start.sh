#!/usr/bin/env bash
# simple helper to manage development containers and diagnostics
# usage: start.sh [--prune] [--yes] [--build] [--diag] [--log] [--frontend|--no-frontend] [--fresh] [--pause] [--input-flags] [--help]

set -euo pipefail

echo "=== Concierge v1.0.0 ==="
echo "Backend → http://localhost:8001"
echo "Frontend → http://localhost:5173"
echo "Flower → http://localhost:5555"
echo "ChromaDB volume enabled for persistent memory"

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

# Define a cleanup function to be called on exit
_cleanup_on_exit() {
    if [ -n "$COMPOSE_LOGS_PID" ]; then echo "Stopping background compose log tail (PID $COMPOSE_LOGS_PID)..." >&2; kill "$COMPOSE_LOGS_PID" 2>/dev/null || true; fi
    if [ -n "$PLAYWRIGHT_LOG_PID" ]; then echo "Stopping Playwright backend log tail (PID $PLAYWRIGHT_LOG_PID)..." >&2; kill "$PLAYWRIGHT_LOG_PID" 2>/dev/null || true; fi
}

# Register the cleanup function to run on EXIT
trap _cleanup_on_exit EXIT

# attempt to free any known ports that might conflict with the
# docker-compose services. this is especially helpful when a stray
# development server (vite, flask, etc.) is still running and prevents
# containers from binding their expected ports. the list below mirrors the
# ports exposed in docker-compose.yml; add or remove entries as needed.
clear_ports() {
    # Helper to find PIDs listening on a port
    _get_pid_on_port() {
        local port="$1"
        local pid=""

        if command -v fuser >/dev/null 2>&1; then
            # Linux-specific, very reliable
            pid=$(fuser -n tcp "$port" 2>/dev/null | awk '{print $1}' || true)
        elif command -v lsof >/dev/null 2>&1; then
            # macOS/Linux
            pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
        elif command -v netstat >/dev/null 2>&1; then
            # Linux (netstat -tulpn) or Windows (netstat -ano)
            if netstat -tulpn >/dev/null 2>&1; then
                pid=$(netstat -tulpn 2>/dev/null | grep -E ":$port\b" | awk '{print $7}' | cut -d/ -f1 | head -n 1 || true)
            else
                # Windows-style netstat -ano
                pid=$(netstat -ano 2>/dev/null | grep -E ":$port\b" | awk '{print $NF}' | sort -u | head -n 1 || true)
            fi
        elif command -v ss >/dev/null 2>&1; then
            # Linux (ss -ltnp)
            pid=$(ss -ltnp 2>/dev/null | grep -E ":$port\b" | awk -F',' '{print $2}' | awk '{print $2}' | cut -d/ -f1 | head -n 1 || true)
        fi

        # Ensure PID is numeric
        if [[ "$pid" =~ ^[0-9]+$ ]]; then
            echo "$pid"
        fi
    }

    ports=(8000 8001 5173 6333)
    echo "Attempting to free known ports..."
    for p in "${ports[@]}"; do
        local pid=$(_get_pid_on_port "$p")
        if [ -n "$pid" ]; then
            echo "  Found process $pid listening on port $p."
            if command -v taskkill >/dev/null 2>&1; then
                echo "  Attempting to kill process $pid with taskkill /F..."
                taskkill /PID "$pid" /F >/dev/null 2>&1 || true
            elif kill -0 "$pid" >/dev/null 2>&1; then
                echo "  Attempting graceful kill of process $pid..."
                kill "$pid" >/dev/null 2>&1 || true
                sleep 1 # Give it a moment to terminate
                if kill -0 "$pid" >/dev/null 2>&1; then
                    echo "  Process $pid still running, forcing kill -9..."
                    kill -9 "$pid" >/dev/null 2>&1 || true
                fi
            else
                echo "  Process $pid no longer exists; skipping kill."
            fi
            # Verify if the port is actually free now
            if [ -n "$(_get_pid_on_port "$p")" ]; then
                echo "  Warning: Port $p is still in use after attempted kill." >&2
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
        echo "Cleaning stale frontend/node_modules..." >&2
        chmod -R u+w "$node_modules_path" 2>/dev/null || true
        rm -rf "$node_modules_path" 2>/dev/null || true

        if [ -d "$node_modules_path" ]; then
            echo "Retrying node_modules removal after first pass..." >&2
            sleep 2 2>/dev/null || true
            rm -rf "$node_modules_path" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ] && command -v powershell.exe >/dev/null 2>&1; then
            echo "Retrying node_modules removal with PowerShell..." >&2
            powershell.exe -NoProfile -Command "Remove-Item -LiteralPath '$node_modules_path' -Recurse -Force" 2>/dev/null || true
        elif [ -d "$node_modules_path" ] && command -v pwsh >/dev/null 2>&1; then
            echo "Retrying node_modules removal with pwsh..." >&2
            pwsh -NoProfile -Command "Remove-Item -LiteralPath '$node_modules_path' -Recurse -Force" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ] && command -v cmd.exe >/dev/null 2>&1; then
            echo "Retrying node_modules removal with Windows cmd.exe rd /s /q..." >&2
            win_path="$node_modules_path"
            if command -v cygpath >/dev/null 2>&1; then
                win_path=$(cygpath -w "$node_modules_path" 2>/dev/null || true)
            elif command -v wslpath >/dev/null 2>&1; then
                win_path=$(wslpath -w "$node_modules_path" 2>/dev/null || true)
            fi
            cmd.exe /C "rd /s /q \"$win_path\"" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ] && command -v node >/dev/null 2>&1; then
            echo "Retrying node_modules removal with Node.js fs.rmSync..." >&2
            node -e "const fs=require('fs'); try { fs.rmSync(process.argv[1], { recursive: true, force: true }); } catch (e) {}" "$node_modules_path" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ] && command -v python >/dev/null 2>&1; then
            echo "Retrying node_modules removal with Python shutil.rmtree..." >&2
            python -c "import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)" "$node_modules_path" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ] && command -v npx >/dev/null 2>&1; then
            echo "Retrying node_modules removal with npx rimraf..." >&2
            npx --yes rimraf "$node_modules_path" 2>/dev/null || true
        fi

        if [ -d "$node_modules_path" ]; then
            echo "Warning: frontend/node_modules still exists after cleanup; npm ci may still fail." >&2
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
  -h, --help display this message

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
FRESH=false
PAUSE=false
INPUT_FLAGS=false
NGROK_URL_SET=false

apply_arg() {
    local arg="$1"
    case "$arg" in
        --build-dist) BUILD_DIST=true ;;
        --prune) PRUNE=true ;;
        --yes) YES=true ;;
        --build) BUILD=true ;;
        --build-dist) BUILD_DIST=true ;;
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
        --fresh) FRESH=true ;;
        --pause) PAUSE=true ;;
        --input-flags) INPUT_FLAGS=true ;;
        --no-docker|--local) NO_DOCKER=true ;;
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
    read -r extra_flags_line
    if [ -n "${extra_flags_line:-}" ]; then
        # shellcheck disable=SC2206
        extra_flags=( $extra_flags_line )
        for arg in "${extra_flags[@]}"; do
            apply_arg "$arg"
        done
    fi
fi

echo "Startup flags:"
echo "  PRUNE=${PRUNE} YES=${YES} BUILD=${BUILD} BUILD_DIST=${BUILD_DIST} DIAG=${DIAG} PORTS=${PORTS} LOGS=${LOGS} TEST=${TEST} STOP=${STOP}"
echo "  FRONTEND=${FRONTEND} NGROK=${NGROK} CLEAR=${CLEAR} FRESH=${FRESH} NO_DOCKER=${NO_DOCKER}"
echo "  DOCKER_BUILD=${DOCKER_BUILD} DOCKER_BUILDX=${DOCKER_BUILDX} PUSH_IMAGE=${PUSH_IMAGE}"
echo "  IMAGE_TAG=${IMAGE_TAG} PLATFORMS=${PLATFORMS}"
if [ -n "${VITE_API_URL_ARG:-}" ]; then
    echo "  VITE_API_URL_ARG=${VITE_API_URL_ARG}"
fi
if [ -n "${VITE_API_URL_DOCKER_ARG:-}" ]; then
    echo "  VITE_API_URL_DOCKER_ARG=${VITE_API_URL_DOCKER_ARG}"
fi

if $PAUSE; then
    echo "Startup paused. Press Enter to continue..."
    read -r _
fi

# --- Teardown Phase ---
# Handle all teardown flags before any startup actions to prevent hangs and clarify execution order.

# Determine if any startup action is requested. If not, --stop will be a terminal action.
IS_STARTUP_ACTION=false
if $BUILD || $CLEAR || $FRESH || $LOGS || $TEST || $DIAG || $DOCKER_BUILD; then
    IS_STARTUP_ACTION=true
fi
# A simple './start.sh' with no flags also implies startup.
if [[ "$#" -eq 0 ]]; then
    IS_STARTUP_ACTION=true
fi

# Consolidate teardown logic. --fresh implies --clear.
if $FRESH; then
    echo "--fresh implies --clear, log clearing, and frontend reinstall."
    CLEAR=true
fi

if $PORTS; then
    show_port_status
    exit 0
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
    echo "Step 1: Building Docker images with no cache..."
    compose build --no-cache || die "Docker build failed"
    echo "Step 2: Creating distribution zip package (concierge-dist.zip)..."
    if [ -f "concierge-dist.zip" ]; then
        rm -f "concierge-dist.zip"
    fi
    # Exclude development artifacts, logs, and local-only data
    zip -r concierge-dist.zip . -x ".git/*" "frontend/node_modules/*" "*/__pycache__/*" "*.pyc" ".env" "volumes/*" "concierge-dist.zip" "start.log" "ngrok.log" "playwright_backend.log" "logs/*" "chroma/*" ".vscode/*"
    echo "concierge-dist.zip created successfully."
    exit 0
}

do_teardown() {
    echo "--- Teardown Phase ---"
    if ! $NO_DOCKER; then
        if $CLEAR || $FRESH; then
            echo "Stopping and removing containers via 'compose down'..."
            compose down || true # Don't die if it fails, might not be running
        elif $STOP; then
            echo "Stopping containers via 'compose stop'..."
            compose stop || true
        fi
    fi
    echo "Stopping any processes on known ports..."
    clear_ports
    if pgrep -f 'ngrok http 8001' >/dev/null 2>&1; then
        echo "Stopping ngrok process..."
        pkill -f 'ngrok http 8001' || true
    fi
    if $FRESH; then
        clear_logs
    fi
    echo "--- Teardown Complete ---"
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
                docker buildx build "${BUILDX_FLAGS[@]}" "${BUILD_ARGS[@]}" . || die "docker buildx build failed"
            fi
        else
            docker build -t "${IMAGE_TAG}" "${BUILD_ARGS[@]}" . || die "docker build failed"
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

do_start_local() {
    echo "Starting local services without Docker"
    clear_logs
    echo "Freeing known ports before local startup..."
    clear_ports
    if $FRONTEND; then
        write_frontend_env_for_local || true
    fi
    start_local_backend
    if wait_for_backend 127.0.0.1 8001 30; then
        echo "Local backend ready."
    else
        echo "Warning: local backend did not become healthy on 127.0.0.1:8001 after first attempt." >&2
        if [ -n "${BACKEND_PID:-}" ]; then
            echo "Stopping backend PID ${BACKEND_PID} and retrying after clearing ports..."
            kill -9 "${BACKEND_PID}" >/dev/null 2>&1 || true
        fi
        clear_ports
        start_local_backend
        if wait_for_backend 127.0.0.1 8001 30; then
            echo "Local backend ready after retry."
        else
            echo "Error: local backend still did not become healthy on 127.0.0.1:8001 after retry." >&2
            show_port_status
            echo "--- tail of backend log ---" >&2
            tail -n 40 logs/backend.log >&2 || true
            die "Local startup failed because the backend could not bind and become ready."
        fi
    fi
    if $FRONTEND; then
        echo "Starting local frontend..."
        start_local_frontend
        if wait_for_frontend 127.0.0.1 5173 30; then
            echo "Local frontend ready."
        else
            echo "Warning: local frontend did not become healthy on 127.0.0.1:5173 after 30s." >&2
        fi
    fi
    echo "Local startup complete."
    exit 0
}

do_start_docker() {
    # --clear and --fresh imply a build is needed.
    if $CLEAR || $FRESH; then
        BUILD=true
    fi

    if $BUILD; then
        echo "Building containers before start..."
        compose build || die "compose build failed"
    fi

    echo "Starting services with compose up -d"
    compose up -d || die "compose up failed"

    if $LOGS; then
        echo "Capturing docker-compose logs to start.log in background..."
        compose logs -f --no-color app frontend > start.log 2>&1 &
        COMPOSE_LOGS_PID=$!
        echo "Background log tail started with PID $COMPOSE_LOGS_PID."
        echo "You can view live logs by running: tail -f start.log"
    fi

    if wait_for_backend 127.0.0.1 8001 30; then
        echo "Backend ready; starting ngrok."
    else
        echo "Backend did not become healthy; starting ngrok anyway." >&2
        show_port_status
    fi
    start_ngrok

    if $FRONTEND; then
        if ! $NGROK_URL_SET; then
            write_frontend_env_for_docker || true
        fi
        install_frontend_dependencies "$FRESH"
        echo "Starting frontend container via docker-compose"
        # Ensure the frontend container is built if not already
        if ! $BUILD; then
            echo "Building frontend container if necessary..."
            compose build frontend || true # Build only frontend if not a full build
        fi
        compose up -d frontend || die "failed to start frontend container"
        if wait_for_frontend 127.0.0.1 5173 30; then
            echo "Frontend container ready."
        else
            echo "Warning: frontend container did not become healthy on 127.0.0.1:5173 after 30s." >&2
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

if $STOP || $CLEAR || $FRESH; then
    do_teardown
fi

if $STOP && ! $IS_STARTUP_ACTION; then
    echo "Stop action complete. No other startup flags detected, so exiting."
    exit 0
fi

if $BUILD_DIST; then
    do_build_dist
fi

if ! $NO_DOCKER; then
    # --- Docker-based workflow ---
    if ! command -v docker >/dev/null 2>&1; then
        die "docker CLI not found; please install Docker"
    fi
    if ! docker info >/dev/null 2>&1; then
        die "docker daemon not running or not accessible"
    fi
    if ! compose version >/dev/null 2>&1; then
        die "docker compose not available (install docker-compose or use newer Docker)"
    fi
else
    do_start_local
fi

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

wait_for_backend() {
    local host=${1:-127.0.0.1}
    local port=${2:-8001}
    local timeout=${3:-30}
    local ticks=0
    local preferred_path=${HEALTH_PATH:-/health}
    local health_paths=()

    # Normalize paths and allow back compatible health endpoints.
    if [ -n "$preferred_path" ]; then
        if [[ "$preferred_path" != /* ]]; then
            preferred_path="/${preferred_path}"
        fi
        health_paths+=("$preferred_path")
    fi
    health_paths+=("/_health" "/api/_health")

    echo "Waiting for backend to become available on ${host}:${port}..."
    while [ "$ticks" -lt "$timeout" ]; do
        if command -v curl >/dev/null 2>&1; then
            for path in "${health_paths[@]}"; do
                if curl -fs "http://${host}:${port}${path}" >/dev/null 2>&1; then
                    echo "Backend is available via ${path}."
                    return 0
                fi
            done
        elif command -v nc >/dev/null 2>&1; then
            if nc -z "$host" "$port" >/dev/null 2>&1; then
                echo "Backend port ${port} is open."
                return 0
            fi
        else
            if (exec 3<>/dev/tcp/${host}/${port}) >/dev/null 2>&1; then
                exec 3>&-
                echo "Backend port ${port} is open."
                return 0
            fi
        fi
        sleep 1
        ticks=$((ticks + 1))
    done

    echo "Warning: backend did not become available on ${host}:${port} after ${timeout}s." >&2
    return 1
}

wait_for_frontend() {
    local host=${1:-127.0.0.1}
    local port=${2:-5173}
    local timeout=${3:-30}
    local ticks=0

    echo "Waiting for frontend to become available on ${host}:${port}..."
    while [ "$ticks" -lt "$timeout" ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -fs "http://${host}:${port}" >/dev/null 2>&1; then
                echo "Frontend is available."
                return 0
            fi
        elif command -v nc >/dev/null 2>&1; then
            if nc -z "$host" "$port" >/dev/null 2>&1; then
                echo "Frontend port ${port} is open."
                return 0
            fi
        else
            # Fallback for very minimal environments
            if (exec 3<>/dev/tcp/${host}/${port}) >/dev/null 2>&1; then
                exec 3>&-
                echo "Frontend port ${port} is open."
                return 0
            fi
        fi
        sleep 1
        ticks=$((ticks + 1))
    done

    echo "Warning: frontend did not become available on ${host}:${port} after ${timeout}s." >&2
    return 1
}

get_ngrok_public_url() {
    local attempt=0
    local body
    local url

    while [ "$attempt" -lt 10 ]; do
        if command -v curl >/dev/null 2>&1; then
            if ! command -v ngrok >/dev/null 2>&1; then
                echo "ngrok executable not found on PATH." >&2
                return 1
            fi

            body=$(curl -s http://127.0.0.1:4040/api/tunnels || true)
        else
            body=""
        fi

        if [ -n "$body" ]; then
            if command -v python3 >/dev/null 2>&1; then
                url=$(printf '%s' "$body" | python3 -c 'import json,sys
                try:
                    data=json.load(sys.stdin)
                    print(next((t.get("public_url","") for t in data.get("tunnels",[]) if t.get("proto") == "https"), ""))
                except Exception:
                    pass' 2>/dev/null)
            elif command -v python >/dev/null 2>&1; then
                url=$(printf '%s' "$body" | python -c 'import json,sys
                try:
                    data=json.load(sys.stdin)
                    print(next((t.get("public_url","") for t in data.get("tunnels",[]) if t.get("proto") == "https"), ""))
                except Exception:
                    pass' 2>/dev/null)
            else
                echo "Warning: Python not found, falling back to grep/sed for ngrok URL parsing." >&2
                # Fallback to grep/sed if no python available
                url=$(printf '%s' "$body" | grep -oE '"public_url"\s*:\s*"https?://[^"]+"' | sed -E 's/.*"(https?:\/\/[^\"]+)".*/\1/' | head -n 1)
            fi
            if [ -n "$url" ]; then
                printf '%s' "$url"
                return 0
            fi
        fi

        attempt=$((attempt + 1))
        sleep 1
    done

    echo "Warning: ngrok public URL not detected after multiple attempts." >&2
    return 1
}

write_frontend_env() {
    local ngrok_url="$1"
    local env_file="frontend/.env.local"
    local tmp_file

    if [ -z "$ngrok_url" ]; then
        return 1
    fi

    mkdir -p "frontend"
    tmp_file=$(mktemp)

    if [ -f "$env_file" ]; then
        grep -vE '^(VITE_API_URL|BACKEND_URL|VITE_API_URL_SET|VITE_API_URL_AUTO_DETECT)=' "$env_file" > "$tmp_file" || true
    fi

    printf 'VITE_API_URL=%s\nBACKEND_URL=%s\nVITE_API_URL_SET=ngrok\nVITE_API_URL_AUTO_DETECT=true\n' "$ngrok_url" "$ngrok_url" >> "$tmp_file"
    mv "$tmp_file" "$env_file"
    echo "Written frontend environment file: ${env_file}"
    echo "  VITE_API_URL=${ngrok_url}"
    return 0
}

find_python() {
    local candidate
    for candidate in python3 python py; do
        if ! command -v "$candidate" >/dev/null 2>&1; then
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

write_frontend_env_for_local() {
    local env_file="frontend/.env.local"
    local tmp_file

    mkdir -p "frontend"
    tmp_file=$(mktemp)

    if [ -f "$env_file" ]; then
        grep -vE '^(VITE_API_URL_LOCAL|VITE_API_URL|BACKEND_URL|VITE_API_URL_SET|VITE_API_URL_AUTO_DETECT)=' "$env_file" > "$tmp_file" || true
    fi

    printf 'VITE_API_URL_LOCAL=http://127.0.0.1:8001\nVITE_API_URL=http://127.0.0.1:8001\nBACKEND_URL=http://127.0.0.1:8001\nVITE_API_URL_SET=local-no-docker\nVITE_API_URL_AUTO_DETECT=false\n' >> "$tmp_file"
    mv "$tmp_file" "$env_file"
    echo "Written local frontend environment file: ${env_file}"
    echo "  VITE_API_URL_LOCAL=http://127.0.0.1:8001"
    echo "  VITE_API_URL_SET=local"
    return 0
}

write_frontend_env_for_docker() {
    local env_file="frontend/.env.local"
    local tmp_file

    mkdir -p "frontend"
    tmp_file=$(mktemp)

    if [ -f "$env_file" ]; then
        grep -vE '^(VITE_API_URL_DOCKER|VITE_API_URL_LOCAL|VITE_API_URL|BACKEND_URL|VITE_API_URL_SET|VITE_API_URL_AUTO_DETECT)=' "$env_file" > "$tmp_file" || true
    fi

    # The browser cannot resolve Docker internal hostnames like `app`; use host-mapped port.
    printf 'VITE_API_URL_DOCKER=http://127.0.0.1:8001\nVITE_API_URL_LOCAL=http://127.0.0.1:8001\nVITE_API_URL=http://127.0.0.1:8001\nBACKEND_URL=http://127.0.0.1:8001\nVITE_API_URL_SET=docker-host\nVITE_API_URL_AUTO_DETECT=false\n' >> "$tmp_file"
    mv "$tmp_file" "$env_file"
    echo "Written docker frontend environment file: ${env_file}"
    echo "  VITE_API_URL=http://127.0.0.1:8001"
    echo "  VITE_API_URL_SET=local"
    return 0
}

start_local_backend() {
    local py
    local py_cmd
    py=$(find_python) || die "Python 3 is required for local backend startup"
    IFS=' ' read -r -a py_cmd <<< "$py"
    mkdir -p logs

    export PORT=8001
    export CORS_ALLOW_ORIGINS='*'
    local backend_cmd
    set -f
    if "${py_cmd[@]}" -m uvicorn --help >/dev/null 2>&1; then
        backend_cmd=(
            "${py_cmd[@]}" -u -m uvicorn app:app
            --host 127.0.0.1 --port 8001 --reload
            --reload-exclude "frontend/node_modules/*"
            --reload-exclude "frontend/.venv/*"
            --reload-exclude "frontend/.git/*"
            --reload-exclude "logs/*"
        )
    else
        backend_cmd=("${py_cmd[@]}" -u app.py)
    fi
    set +f

    echo "Starting local backend with: ${backend_cmd[*]}"
    echo "  (Logs will be in logs/backend.log)"
    nohup "${backend_cmd[@]}" > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Local backend started with PID ${BACKEND_PID}; logs are in logs/backend.log"
}

start_local_frontend() {
    echo "Starting local frontend dev server"

    local package_lock="frontend/package-lock.json"
    local node_modules_dir="frontend/node_modules"
    local should_install=false

    if [ ! -d "$node_modules_dir" ]; then
        should_install=true
        echo "frontend/node_modules missing; installing dependencies"
    elif [ -f "$package_lock" ] && [ "$package_lock" -nt "$node_modules_dir" ]; then
        should_install=true
        echo "frontend/package-lock.json is newer than node_modules; reinstalling dependencies"
    fi

    if [ "$should_install" = true ]; then
        if [ -f "$package_lock" ]; then
            npm --prefix frontend ci --no-audit --no-fund || die "npm ci failed"
        else
            npm --prefix frontend install --no-audit --no-fund || die "npm install failed"
        fi
    else
        echo "frontend dependencies are already installed and up to date; skipping install"
    fi

    mkdir -p logs
    nohup npm --prefix frontend run dev -- --host > logs/frontend.log 2>&1 &
    echo "  (Logs will be in logs/frontend.log)"
    FRONTEND_PID=$!
    echo "Local frontend started with PID ${FRONTEND_PID}; logs are in logs/frontend.log"
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
        if [ -f "frontend/package-lock.json" ]; then
            echo "Installing frontend dependencies via npm ci..."
            if ! npm --prefix frontend ci --no-audit --no-fund --loglevel=error; then
                echo "npm ci failed; attempting npm install fallback" >&2
                cleanup_frontend_node_modules
                npm --prefix frontend cache clean --force --loglevel=error >/dev/null 2>&1 || true
                npm --prefix frontend install --no-audit --no-fund --loglevel=error || die "npm install failed"
            fi
        else
            echo "Installing frontend dependencies via npm install..."
            npm --prefix frontend install --no-audit --no-fund || die "npm install failed"
        fi
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
    if pgrep -f 'ngrok http 8001' >/dev/null 2>&1; then
        echo "ngrok tunnel already running for port 8001."
    else
        echo "Starting ngrok tunnel for backend on port 8001..."
        nohup ngrok http 8001 > ngrok.log 2>&1 &
        NGROK_PID=$!
        echo "ngrok started with PID ${NGROK_PID}; logs are in ngrok.log"
    fi

    local ngrok_url
    if ngrok_url=$(get_ngrok_public_url); then
        echo "Detected ngrok public URL: ${ngrok_url}"
        if write_frontend_env "$ngrok_url"; then
            NGROK_URL_SET=true
        else
            echo "Warning: failed to write frontend env file." >&2
        fi
    else
        echo "Warning: could not detect ngrok public URL." >&2
    fi
}

if $PRUNE; then
    do_prune
fi

if $DIAG; then
    do_diag
fi

# Optional: build/push a repository Docker image for deployment/test
if $DOCKER_BUILD; then
    do_docker_build
fi

do_start_docker

# if --test was requested, kick off Playwright and tail backend logs
if $TEST; then
    do_test
fi

echo "start.sh complete."
