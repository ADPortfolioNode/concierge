#!/usr/bin/env bash
set -euo pipefail

echo "Building concierge:staging image..."
docker build -t concierge:staging .

echo "Stopping existing staging container (if any)..."
docker rm -f concierge_staging || true

echo "Starting staging container on port 8001..."
docker run -d --name concierge_staging -p 8001:8001 --restart=unless-stopped concierge:staging

echo "Staging deployment complete."
