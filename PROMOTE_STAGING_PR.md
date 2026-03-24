This repo uses a safe verify-and-promote flow that only auto-merges when the CI verifier and staging checks pass and `SKIP_PROMOTE` is unset in the environment.

To create a promotion PR (staging → main) that will be merged automatically by the existing `scripts/verify_and_promote.py` and workflows once repository secrets are present, run the steps below from a machine with `git` and the GitHub CLI (`gh`) configured.

1. Ensure you have the necessary secrets configured in the repository settings (or in your local environment while testing): `VERCEL_ALIAS` (staging alias) and optionally `VERCEL_TOKEN`.
2. Create a promotion branch locally (optional — you can use `staging` directly):

   git checkout -b promote/staging-to-main

3. Push the branch to origin:

   git push origin promote/staging-to-main

4. Create the PR using `gh` (this creates the GitHub PR; CI will run on `staging` or the branch push as configured):

   gh pr create --base main --head promote/staging-to-main --title "chore(promote): promote staging to main (auto)" --body "Promotion PR: verifier will run and auto-merge when green and SKIP_PROMOTE is unset." --label "auto-promote"

Notes:
- The repo already includes `scripts/verify_and_promote.py` and a workflow that runs on pushes to `staging`. That verifier will attempt to create and merge the promotion PR when `SKIP_PROMOTE=false` and required secrets are available.
- If you want the verifier to run on this PR specifically, ensure the PR's branch is built by CI (push to `staging` or push the branch and set the same vercel alias if required).

If you want me to prepare a helper branch and file changes for you to push, tell me and I will create the branch contents here and provide the exact `git` commands to run locally.
