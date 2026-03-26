#!/usr/bin/env python3
"""Interactive helper to set GitHub Actions secrets needed for verification/promote.

This script prompts for a GitHub PAT (or uses GITHUB_TOKEN from env) and then
asks which Vercel/GitHub secrets you'd like to add. It calls
`scripts/set_github_secret.py` for each secret, passing the secret value via an
environment variable (so values are not visible in the command-line args).

Run locally (recommended):
  python scripts/automate_setup.py

Security: Do NOT paste tokens in chat. Run this locally where you control the
environment. Tokens entered are used only to set repository secrets via the
GitHub API and are not logged.
"""
import os
import shlex
import subprocess
import sys
from getpass import getpass

REPO = "ADPortfolioNode/concierge"
SETTER = os.path.join("scripts", "set_github_secret.py")


def ask_yes_no(prompt, default=True):
    yn = "[Y/n]" if default else "[y/N]"
    r = input(f"{prompt} {yn} ").strip().lower()
    if not r:
        return default
    return r[0] == 'y'


def prompt_secret(name, secret=True):
    if secret:
        return getpass(f"Enter value for {name} (input hidden): ")
    else:
        return input(f"Enter value for {name}: ").strip()


def run_setter(github_token, secret_name, secret_value):
    env = dict(os.environ)
    env["GITHUB_TOKEN"] = github_token
    # Pass secret value via env var named after the secret to avoid exposing it
    env[secret_name] = secret_value
    cmd = [sys.executable, SETTER, "--repo", REPO, "--name", secret_name]
    print("-> Setting secret", secret_name)
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, env=env, text=True)
        print(res.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to set {secret_name}:", e.stderr.strip())
        return False


def main():
    print("Automated secret setup helper for ADPortfolioNode/concierge")
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Provide a GitHub Personal Access Token (scopes: repo, admin:repo_hook)")
        github_token = getpass("GitHub PAT (input hidden): ")
    if not github_token:
        print("No GitHub token provided — aborting.")
        sys.exit(1)

    # Candidate secrets to set
    candidates = [
        ("VERCEL_BYPASS_TOKEN", True, "Bypass token for protected preview deployments"),
        ("VERCEL_TOKEN", True, "Vercel API token (for deployments/automation)"),
        ("VERCEL_ORG_ID", False, "Vercel organization id"),
        ("VERCEL_PROJECT_ID", False, "Vercel project id"),
        ("VERCEL_ALIAS", False, "Staging alias/URL (e.g. deoismconcierge-git-staging-...vercel.app)"),
        ("ALLOW_AUTO_MERGE", False, "Set to 'true' to allow CI auto-merge (optional)")
    ]

    results = {}
    for name, is_secret, desc in candidates:
        print(f"\n{name}: {desc}")
        if ask_yes_no(f"Set {name}?", default=False):
            val = prompt_secret(name, secret=is_secret)
            if not val:
                print("Empty value — skipping")
                continue
            ok = run_setter(github_token, name, val)
            results[name] = ok

    print("\nSummary:")
    for k, v in results.items():
        print(f" - {k}: {'OK' if v else 'FAILED'}")

    # Optionally run verifier locally if bypass token was set
    if results.get("VERCEL_BYPASS_TOKEN"):
        if ask_yes_no("Run verifier (dry-run) now using the bypass token?", default=True):
            alias = os.environ.get("VERCEL_ALIAS") or input("Staging URL (or press Enter to use default): ").strip()
            if not alias:
                alias = "https://deoismconcierge-git-staging-adportfolionodes-projects.vercel.app"
            token = getpass("Enter bypass token to use for this run (input hidden): ")
            if not token:
                print("No token provided — skipping verifier run.")
            else:
                # Append token as query param to alias
                if "?" in alias:
                    url = f"{alias}&__vercel_bypass_token={shlex.quote(token)}"
                else:
                    url = f"{alias}?__vercel_bypass_token={shlex.quote(token)}"
                env = dict(os.environ)
                env["SKIP_PROMOTE"] = "1"
                env["VERCEL_ALIAS"] = url
                cmd = [sys.executable, os.path.join("scripts", "verify_and_promote.py")]
                print("Running verifier (dry-run)...")
                subprocess.run(cmd, env=env)


if __name__ == '__main__':
    main()
