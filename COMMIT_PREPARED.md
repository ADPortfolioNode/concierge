Prepared commit: remove committed frontend build artifacts

What I changed:
- Added `public` to .gitignore to avoid committing generated frontend assets.
- Removed committed files under `public/` that are produced by the frontend build.

Next steps (run locally):
1. Review changes: `git status` and `git diff`.
2. Stage and commit:
   - `git add -A`
   - `git commit -m "chore: remove committed frontend build artifacts and ignore /public/"`
3. Push your branch and open a PR against `staging` to trigger CI.

Security reminder: rotate any exposed deployment tokens and add new tokens to GitHub Actions secrets.

If you want, I can run `git` commands here or create the PR for you after you rotate secrets.
