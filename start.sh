#!/bin/sh
set -e

exec gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WORKERS:-2}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --log-level "${LOG_LEVEL:-info}"
