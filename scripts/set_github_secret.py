#!/usr/bin/env python3
"""Set a GitHub Actions repository secret using the GitHub REST API.

Usage examples:
  # Bash
  export GITHUB_TOKEN="<your_personal_access_token>"
  python scripts/set_github_secret.py --repo ADPortfolioNode/concierge --name VERCEL_ALIAS --value "deoismconcierge-git-staging-adportfolionodes-projects.vercel.app"

  # PowerShell
  $env:GITHUB_TOKEN = '<your_personal_access_token>'
  python .\scripts\set_github_secret.py --repo ADPortfolioNode/concierge --name VERCEL_ALIAS --value '...'

Requires: pip install requests pynacl
Do NOT paste tokens in chat; run this locally in your environment.
"""
import argparse
import base64
import os
import sys

import requests
from nacl import encoding, public


def encrypt_secret(public_key: str, secret_value: str) -> str:
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="owner/repo, e.g. ADPortfolioNode/concierge")
    p.add_argument("--name", required=True, help="secret name, e.g. VERCEL_TOKEN")
    p.add_argument("--value", required=False, help="secret value (optional; can be provided via env var)")
    p.add_argument("--token", required=False, help="GitHub PAT (optional; prefer GITHUB_TOKEN env var)")
    args = p.parse_args()

    github_token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not github_token:
        print("Error: set GITHUB_TOKEN environment variable or pass --token", file=sys.stderr)
        sys.exit(2)

    secret_value = args.value or os.environ.get(args.name) or os.environ.get("SECRET_VALUE")
    if not secret_value:
        print(f"Error: provide secret value via --value or env var {args.name}", file=sys.stderr)
        sys.exit(3)

    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}

    # Get the repo public key
    owner_repo = args.repo
    url_key = f"https://api.github.com/repos/{owner_repo}/actions/secrets/public-key"
    r = requests.get(url_key, headers=headers, timeout=10)
    r.raise_for_status()
    j = r.json()
    public_key = j["key"]
    key_id = j["key_id"]

    encrypted_value = encrypt_secret(public_key, secret_value)

    put_url = f"https://api.github.com/repos/{owner_repo}/actions/secrets/{args.name}"
    payload = {"encrypted_value": encrypted_value, "key_id": key_id}
    r = requests.put(put_url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    print(f"Secret {args.name} set for {owner_repo}")


if __name__ == "__main__":
    main()
