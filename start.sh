#!/usr/bin/env bash
# simple helper to manage development containers and diagnostics
# usage: start.sh [--prune] [--yes] [--build] [--diag] [--help]

set -euo pipefail

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
  --clear    stop and remove running compose services (docker-compose down)
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
CLEAR=false

for arg in "$@"; do
    case "$arg" in
        --prune) PRUNE=true ;;
        --yes) YES=true ;;
        --build) BUILD=true ;;
        --diag) DIAG=true ;;
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
        docker system prune -af
    else
        echo "Skipping prune."
    fi
fi

if $BUILD; then
    echo "Building containers..."
    docker-compose build
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
    echo "Clearing environment: docker-compose down; up -d --build"
    docker-compose down || true
    docker-compose up -d --build
else
    # always attempt to tear down first to avoid port conflicts, then bring up
    echo "Ensuring any existing services are stopped (docker-compose down)"
    docker-compose down || true
    if $BUILD; then
        echo "Building containers before start..."
        docker-compose build
    fi
    echo "Starting services with docker-compose up -d"
    docker-compose up -d
fi

echo "start.sh complete."
