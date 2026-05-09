#!/usr/bin/env bash
set -euo pipefail

CANARY_IMAGE=concierge:canary
CANARY_CONTAINER=concierge_canary_test
CANARY_PORT=8002

echo "Building canary image..."
docker build -t ${CANARY_IMAGE} .

echo "Stopping old canary container if present..."
docker rm -f ${CANARY_CONTAINER} || true

echo "Starting canary container on port ${CANARY_PORT}..."
docker run -d --name ${CANARY_CONTAINER} -p ${CANARY_PORT}:8001 ${CANARY_IMAGE}

echo "Waiting for canary /health..."
for i in {1..30}; do
  if curl -sSf http://localhost:${CANARY_PORT}/health >/dev/null 2>&1; then
    echo "canary healthy"; break
  fi
  sleep 1
done

echo "Running smoke endpoint checks against canary..."
BASE_URL="http://localhost:${CANARY_PORT}" python scripts/check_endpoints.py || (
  echo "Smoke checks failed against canary; aborting promotion" >&2
  docker logs ${CANARY_CONTAINER} --tail 200 || true
  docker rm -f ${CANARY_CONTAINER} || true
  exit 2
)

echo "Smoke checks passed; promoting canary to staging..."
./scripts/promote_canary.sh

echo "Cleaning up test canary container"
docker rm -f ${CANARY_CONTAINER} || true

echo "Canary smoke + promote completed successfully."
