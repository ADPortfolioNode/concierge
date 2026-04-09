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
        elif command -v netstat >/dev/null 2>&1 || command -v ss >/dev/null 2>&1; then
            # Try several netstat/ss/awk combinations to locate PID (Linux/macOS)
            pid=$(netstat -tulpn 2>/dev/null | grep -E ":$p( |$)" | awk '{print $7}' | cut -d/ -f1 2>/dev/null || true)
            if [ -z "$pid" ] && command -v ss >/dev/null 2>&1; then
                pid=$(ss -ltnp 2>/dev/null | grep -E ":$p( |$)" | awk -F',' '{print $2}' | awk '{print $2}' | cut -d/ -f1 2>/dev/null || true)
            fi
            if [ -n "$pid" ]; then
                # ensure pid is numeric before attempting kill
                if echo "$pid" | grep -qE '^[0-9]+$'; then
                    echo "killing process $pid listening on port $p"
                    kill -9 $pid || true
                fi
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
  --no-ngrok      do not start ngrok tunnel even if ngrok is installed
    --docker-build    run `docker build` for the repository root Dockerfile
    --buildx          use `docker buildx build` (supports --platform)
    --push-image      push the built image to the configured registry (requires `--image-tag`)
    --image-tag=<name:tag>  override image tag used for build/push (default: concierge:latest)
    --platform=<list> comma-separated platforms for buildx (default: linux/amd64)
    --build-frontend        build frontend during Docker build (passes BUILD_FRONTEND=1)
    --install-full-reqs     install `requirements.full.txt` instead of `requirements.txt`
    --vite-api-url=<url>    pass VITE_API_URL build-arg into frontend build
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
# frontend will be started by default; use --no-frontend to skip
FRONTEND=true
# ngrok will be started automatically if available; use --no-ngrok to skip
NGROK=true
CLEAR=false

for arg in "$@"; do
    case "$arg" in
        --prune) PRUNE=true ;;
        --yes) YES=true ;;
        --build) BUILD=true ;;
        --diag) DIAG=true ;;
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
        --frontend) FRONTEND=true ;;  # explicit enable (redundant)
        --no-frontend) FRONTEND=false ;;
        --no-ngrok) NGROK=false ;;
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
        return
    fi

    echo "Starting ngrok tunnel for backend on port 8001..."
    nohup ngrok http 8001 > ngrok.log 2>&1 &
    NGROK_PID=$!
    echo "ngrok started with PID ${NGROK_PID}; logs are in ngrok.log"
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
        compose version || true
        echo
        echo "--- docker ps -a ---"
        docker ps -a || true
        echo "--- end diagnostics ---"
    } | tee start.log
fi

# Optional: build/push a repository Docker image for deployment/test
if $DOCKER_BUILD; then
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
fi

if $CLEAR; then
    # --clear implies restart with build to avoid stale images
    echo "Clearing environment: compose down; up -d --build"
    echo "freeing known ports before tear down/start"
    clear_ports
    compose down || true
    compose up -d --build || die "compose up failed"
    start_ngrok
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
    start_ngrok
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
            if ! npm --prefix frontend ci --no-audit --no-fund; then
                echo "npm ci failed; attempting npm install fallback" >&2
                if ! npm --prefix frontend install --no-audit --no-fund; then
                    die "npm install failed"
                fi
            fi
        else
            npm --prefix frontend install --no-audit --no-fund || die "npm install failed"
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
        # use docker ps filter to reliably detect exited containers by name
        if docker ps -a --filter "name=quesarc_${svc}" --filter "status=exited" --format '{{.Names}}' | grep -q .; then
            echo "${svc^} container exited; here are the last 20 lines of its log:" >&2
            compose logs $svc --tail=20 >&2
        fi
    done
fi

echo "start.sh complete."
