#!/usr/bin/env bash
set -euo pipefail

echo "Rolling back canary: removing canary container and image if present..."
docker rm -f concierge_canary || true
docker rmi concierge:canary || true

echo "Rollback complete."
