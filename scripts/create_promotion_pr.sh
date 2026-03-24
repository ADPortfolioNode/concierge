#!/usr/bin/env bash
# Helper: create a promotion PR (staging -> main) using the GitHub CLI
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install and login with 'gh auth login' first." >&2
  exit 2
fi

if [ -z "${VERCEL_ALIAS:-}" ]; then
  echo "Warning: VERCEL_ALIAS not set in environment. The verifier needs this to target staging." >&2
fi

BRANCH=${1:-promote/staging-to-main}
TITLE="chore(promote): promote staging to main (auto)"
BODY="Promotion PR: verifier will run and auto-merge when green and SKIP_PROMOTE is unset."

echo "Creating branch: $BRANCH (locally)"
git checkout -b "$BRANCH"
git push -u origin "$BRANCH"

echo "Creating GitHub PR..."
gh pr create --base main --head "$BRANCH" --title "$TITLE" --body "$BODY" --label "auto-promote"

echo "Promotion PR created. CI will run on the pushed branch. Verify logs in Actions; when ready, set SKIP_PROMOTE=false to allow auto-merge."
