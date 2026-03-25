# Secrets rotation and GitHub Actions secret setup

This document describes how to rotate the Vercel token and add the required repository secrets so the staging verifier and promotion workflow can run.

Required secrets (names used by workflows):
- `VERCEL_TOKEN` — Vercel personal token with deployment access
- `VERCEL_ORG_ID` — Vercel organization id (from Vercel project settings)
- `VERCEL_PROJECT_ID` — Vercel project id (from Vercel project settings)
- `VERCEL_ALIAS` — staging alias hostname, e.g. `deoismconcierge-git-staging-adportfolionodes-projects.vercel.app`
- `AUTO_MERGE` — set to `1` if you want CI to attempt auto-merge (requires ALLOW_AUTO_MERGE)
- `ALLOW_AUTO_MERGE` — safety gate; set to `true` or `yes` to allow merging

## Rotate Vercel token (recommended immediately if token exposed)
1. Sign into Vercel (https://vercel.com).
2. Open Settings → Tokens (Personal Tokens) and create a new token. Copy the token value.
3. Optionally revoke the old token after confirming CI runs with the new token.

## Add secrets via GitHub web UI (recommended)
1. Open your repository on GitHub: https://github.com/ADPortfolioNode/concierge
2. Go to `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.
3. Add the secrets listed above one-by-one. Use the exact names.

## Add secrets via GitHub CLI (script)
1. Install and authenticate `gh`: https://cli.github.com/
2. Export the variables locally in your shell, for example (PowerShell):

```powershell
$env:VERCEL_TOKEN = "<your-new-token>"
$env:VERCEL_ALIAS = "deoismconcierge-git-staging-adportfolionodes-projects.vercel.app"
$env:VERCEL_ORG_ID = "<your-org-id>"
$env:VERCEL_PROJECT_ID = "<your-project-id>"
$env:AUTO_MERGE = "0"
$env:ALLOW_AUTO_MERGE = "false"
./scripts/setup_github_secrets.sh
```

Or (Bash):

```bash
export VERCEL_TOKEN="<your-new-token>"
export VERCEL_ALIAS="deoismconcierge-git-staging-adportfolionodes-projects.vercel.app"
export VERCEL_ORG_ID="<your-org-id>"
export VERCEL_PROJECT_ID="<your-project-id>"
export AUTO_MERGE=0
export ALLOW_AUTO_MERGE=false
scripts/setup_github_secrets.sh
```

## Running the staging verify workflow (dry-run)
1. Keep `AUTO_MERGE=0` and `ALLOW_AUTO_MERGE=false` to avoid auto-merging.
2. Push a branch to `staging` or open a PR against `staging` to trigger `.github/workflows/staging-verify-and-promote.yml`.
3. Monitor Actions → workflow run for logs. The verifier will check `/health` and asset availability.

## Enabling auto-merge (use with caution)
1. Only enable after you trust the verifier. Set `AUTO_MERGE=1` and `ALLOW_AUTO_MERGE=true` in GitHub secrets.
2. The verifier will create a PR to promote `staging` → `main` and attempt to merge when both flags are set.

## Security guidance
- Do not paste tokens into chat or commit them to the repo. Rotate any token that was exposed.
- Limit token permissions to the minimum required for CI (deployment scope only).
- Consider creating a short-lived token and store it in GitHub Actions secrets.
