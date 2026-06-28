# Git History Cleanup (Secret Leaks + Large Artifacts)

This document explains how to recover when real secrets (API keys) were accidentally committed, or when large local-only directories polluted the repo, and GitHub push protection is blocking you.

**Never commit real keys.** The project uses:
- `.gitignore` and `.dockerignore` that exclude `.env`, `.env.*`, `!.env.example` (only), `*.pem`, `secrets/`, `.migration-backup/`, etc.
- Code centralized in `config/settings.py` (see the earlier refactor) — no `os.getenv("OPENAI_API_KEY")` etc. scattered in source.

---

## Symptoms You Are Seeing
- `error: src refspec git does not match any` or `fatal: 'or' does not appear to be a git repository`
- GitHub: "Push cannot contain secrets", "repository rule violations", or secret scanning blocks even with `--force`.

Common cause of the refspec error: typing **multiple commands on one line**, e.g.

```bash
# BAD
git push --force-with-lease origin main  git status
git push --force-with-lease or
```

**Rule:** One complete command per line. Press Enter. Wait. Then next.

---

## Step-by-Step Fix (Git Bash / MINGW64 — the shell shown in your errors)

### 1. Clean any local index pollution (e.g. .migration-backup)
This was a one-time local artifact that ended up tracked (3999+ files).

```bash
git rm -r --cached .migration-backup
git commit -m "chore(git): untrack .migration-backup/ (local artifact, already gitignored)"
```

### 2. Install the history rewrite tool
```bash
python -m pip install git-filter-repo
git filter-repo --help   # should show usage; if not, open a fresh terminal
```

### 3. Create `replacements.txt` (in the project root)
**Do this privately.** Collect the *exact* strings GitHub flagged (from its emails or the secret scanning UI).

Example format (left = real leaked value, right = replacement):

```
sk-abc123def456ghi789jkl012mno345pqr678==>sk-REDACTED-OPENAI
xai-987zyx654wvu321tsr098qpo765nml432==>xai-REDACTED-GROK
AIzaSyDqWvR8tYpL9mN3kJ7hG5fD2sA4bC6eF8gH==>AIzaSyREDACTED-GEMINI
```

Create the file (example using heredoc in Git Bash):

```bash
cat > replacements.txt << 'EOT'
sk-REALVALUE1==>sk-REDACTED
xai-REALVALUE2==>xai-REDACTED
AIzaSyREALVALUE3==>AIzaSyREDACTED
EOT
```

**Do not commit or push `replacements.txt`.** Delete it after use.

### 4. Rewrite history (the magic command — run as ONE line)
This redacts the secrets **and** purges the backup dir from the entire history:

```bash
git filter-repo --replace-text replacements.txt --path .migration-backup --invert-paths --force
```

- Expect completely new commit SHAs.
- Your working tree files stay on disk (the local `.migration-backup/` dir will now appear untracked because of .gitignore — that's correct).

### 5. Inspect the result
```bash
git status
git log --oneline -5
```

The top hash should be different from what you had before (e.g. not `1038caa`).

Verify secrets and junk are gone from index:
```bash
git ls-files | grep -E 'migration-backup' || echo "No migration-backup in index (good)"
git ls-files | grep -E '\.env' || echo "No extra .env files"
```

(You can also try `git log -S 'sk-' --oneline` — it should be quiet or only show the replacement commit.)

### 6. Push (single clean command)
```bash
git push --force-with-lease origin main
```

### 7. GitHub side (you will almost certainly need this)
- If the web UI still shows a push protection error for **this** push, use the **"Unblock this push"** (or bypass) button/link. GitHub gives a few of these.
- After the push succeeds:
  1. Go to your repo on GitHub → **Settings** → **Code security and analysis** (or Security tab) → **Secret scanning alerts**.
  2. For each old alert, mark as **Revoked**, add note "History rewritten with git-filter-repo; keys rotated", then resolve.
- **Immediately rotate/revoke** the three keys (Gemini, OpenAI, Grok/xAI) at their provider consoles. Treat them as public.

### 8. Clean up locally
```bash
rm -f replacements.txt
# (optional) rm -rf .migration-backup   # only if you no longer need the backup
```

Future normal pushes:
```bash
git push
```

---

## Alternative (simpler) rewrite if you only care about the keys
If you don't care about also removing the backup dir from history:

```bash
git filter-repo --replace-text replacements.txt --force
```

Then do a normal commit for the index cleanup if you still have the dir tracked:
```bash
git rm -r --cached .migration-backup
git commit -m "chore(git): untrack migration-backup"
git push --force-with-lease origin main
```

---

## PowerShell / Windows notes
The same logic applies, but use PowerShell quoting carefully.

Install:
```powershell
python -m pip install git-filter-repo
```

For heredoc-style replacements.txt, use an editor or:
```powershell
@"
sk-REAL==>sk-REDACTED
xai-REAL==>xai-REDACTED
"@ | Out-File -Encoding utf8 replacements.txt
```

Then the filter-repo and push commands are identical.

---

## After a successful cleaned push
- Anyone who previously cloned must delete their clone and re-clone.
- Your local repo now has new history. Do not mix old clones.
- The current `.env.example` only contains safe placeholders.
- Code no longer has raw key strings thanks to the settings refactor.

## Prevention
- Always use `.env` (gitignored) + `.env.example` (placeholders only).
- Run `git status` and `git ls-files | grep -E '\.env|secret'` before committing.
- The settings.py centralization means you never need to write `os.getenv("FOO_API_KEY")` again.
- Add `docs/git-history-cleanup.md` to your mental checklist if GitHub ever complains again.

---

If you followed the steps above one command at a time and the push succeeded, the issue is resolved.

Report back with the final successful `git push` output or a screenshot of the GitHub commit list (new hashes) for verification.