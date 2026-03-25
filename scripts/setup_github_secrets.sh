#!/usr/bin/env bash
set -euo pipefail

echo "Helper: set GitHub Actions secrets for ADPortfolioNode/concierge"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI and authenticate first: https://cli.github.com/"
  echo "Example (Windows PowerShell):" 
  echo "  winget install --id GitHub.cli" 
  echo "  gh auth login"
  exit 2
fi

REPO="ADPortfolioNode/concierge"

set_secret() {
  name="$1"
  value_var="$2"
  value="${!value_var:-}"
  if [ -z "$value" ]; then
    echo "Environment variable $value_var is not set; skipping $name"
    return
  fi
  echo "Setting secret $name..."
  gh secret set "$name" --body "$value" --repo "$REPO"
}

# Expected environment variables (export before running):
# VERCEL_TOKEN, VERCEL_ALIAS, VERCEL_ORG_ID, VERCEL_PROJECT_ID, AUTO_MERGE, ALLOW_AUTO_MERGE

set_secret VERCEL_TOKEN VERCEL_TOKEN
set_secret VERCEL_ALIAS VERCEL_ALIAS
set_secret VERCEL_ORG_ID VERCEL_ORG_ID
set_secret VERCEL_PROJECT_ID VERCEL_PROJECT_ID
set_secret AUTO_MERGE AUTO_MERGE
set_secret ALLOW_AUTO_MERGE ALLOW_AUTO_MERGE

echo "Done. Verify secrets in the repository settings → Secrets and variables → Actions."
