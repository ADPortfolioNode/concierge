#!/usr/bin/env bash
# Exit codes: 1 = build needed, 0 = skip build
# This script is intended for use as Vercel's "Ignored Build Step" command.
# It returns exit code 1 when files that should trigger a build changed between
# the previous and current commit SHAs provided by Vercel environment vars.

set -euo pipefail

PREV="${VERCEL_GIT_PREVIOUS_SHA:-}"
CUR="${VERCEL_GIT_COMMIT_SHA:-}"

if [ -z "$PREV" ] || [ -z "$CUR" ]; then
  # If we can't determine SHAs, be conservative and trigger a build
  exit 1
fi

# List of paths that should trigger a build when changed
TRIGGERS='^(frontend/|requirements.txt|app.py|vercel.json)'

# Get changed files between the two SHAs
changed_files=$(git diff --name-only "$PREV" "$CUR" || true)

echo "Changed files between $PREV and $CUR:" >&2
echo "$changed_files" >&2

echo "$changed_files" | grep -E "$TRIGGERS" >/dev/null && exit 1 || exit 0
