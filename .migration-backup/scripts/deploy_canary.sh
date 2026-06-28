#!/usr/bin/env bash
set -euo pipefail

echo "Building concierge:canary image..."
docker build -t concierge:canary .

echo "Stopping existing canary container (if any)..."
docker rm -f concierge_canary || true

echo "Starting canary container on port 8003..."
docker run -d --name concierge_canary -p 8003:8001 --restart=unless-stopped concierge:canary

echo "Canary deployment complete."
