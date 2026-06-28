#!/usr/bin/env bash
set -euo pipefail

echo "Promoting canary to staging..."

echo "Stopping staging container (if any)..."
docker rm -f concierge_staging || true

echo "Tagging canary image as staging..."
docker tag concierge:canary concierge:staging

echo "Starting staging container from canary image on port 8001..."
docker run -d --name concierge_staging -p 8001:8001 --restart=unless-stopped concierge:staging

echo "Promotion complete."
