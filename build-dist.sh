#!/bin/sh
set -e

echo "Building Docker distribution..."
docker compose build

echo "Creating concierge-dist.zip..."
zip -r concierge-dist.zip . -x "*/.git/*" "*/node_modules/*" "*/__pycache__/*" "*/.venv/*" "*frontend/node_modules/*" "*dist/*" "*.gitignore" "*.DS_Store" "*/.idea/*" "*/.vscode/*"

echo "Done. Created concierge-dist.zip"
