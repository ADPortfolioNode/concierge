#!/usr/bin/env python3
"""Verify a staging deployment and optionally create/merge a promotion PR.

Usage: run in GH Actions with env vars set: VERCEL_ALIAS, GITHUB_TOKEN
Optional: SKIP_PROMOTE=1 to only verify, AUTO_MERGE=1 to auto-merge PR after creation.
"""
import os
import re
import sys
import time
from urllib.parse import urljoin

try:
    import requests
except Exception:
    print("requests library required. Install with pip install requests", file=sys.stderr)
    sys.exit(2)


def getenv(name, default=None):
    v = os.environ.get(name)
    return v if v is not None else default


def check_health(base):
    url = urljoin(base, "/health")
    print(f"Checking health: {url}")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text


def fetch_index_and_check_assets(base):
    url = base
    print(f"Fetching root HTML: {url}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    html = r.text
    assets = set(re.findall(r'(?:src|href)\s*=\s*"(/assets/[^"]+)"', html))
    print(f"Found {len(assets)} asset references")
    failed = []
    for asset in assets:
        asset_url = urljoin(base, asset)
        print(f"Checking asset: {asset_url}")
        try:
            h = requests.head(asset_url, timeout=10, allow_redirects=True)
            if h.status_code >= 400:
                print(f"Asset returned {h.status_code}")
                failed.append((asset_url, h.status_code))
        except Exception as e:
            print(f"Asset check error: {e}")
            failed.append((asset_url, str(e)))
    return failed


def create_promotion_pr(repo, source_branch, target_branch, github_token, title, body):
    api = f"https://api.github.com/repos/{repo}/pulls"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}
    payload = {"title": title, "body": body, "head": source_branch, "base": target_branch}
    r = requests.post(api, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def merge_pr(repo, pr_number, github_token):
    api = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}
    r = requests.put(api, json={"merge_method": "squash"}, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    alias = getenv("VERCEL_ALIAS")
    if not alias:
        print("VERCEL_ALIAS must be set (e.g. my-site-staging.vercel.app)")
        sys.exit(3)
    base = alias if alias.startswith("http") else f"https://{alias}"

    # Basic checks
    try:
        health = check_health(base)
        print("Health OK:", health)
    except Exception as e:
        print("Health check failed:", e)
        sys.exit(4)

    try:
        failed_assets = fetch_index_and_check_assets(base)
        if failed_assets:
            print("Asset checks failed:", failed_assets)
            sys.exit(5)
    except Exception as e:
        print("Index/asset check failed:", e)
        sys.exit(6)

    print("All staging checks passed")

    # Promotion step
    skip = getenv("SKIP_PROMOTE")
    if skip and skip.lower() in ("1", "true", "yes"):
        print("SKIP_PROMOTE set; exiting after verification")
        return

    github_token = getenv("GITHUB_TOKEN") or getenv("GH_TOKEN")
    if not github_token:
        print("No GITHUB_TOKEN; cannot create PR. Set GITHUB_TOKEN in env.")
        sys.exit(7)

    repo = getenv("GITHUB_REPOSITORY")
    if not repo:
        print("GITHUB_REPOSITORY not set; using ADPortfolioNode/concierge as default")
        repo = "ADPortfolioNode/concierge"

    source = getenv("SOURCE_BRANCH", "staging")
    target = getenv("TARGET_BRANCH", "main")
    title = getenv("PR_TITLE", "chore: promote staging to main (verified)")
    body = getenv("PR_BODY", "Automated promotion: staging verified by CI")

    try:
        pr = create_promotion_pr(repo, source, target, github_token, title, body)
        pr_number = pr.get("number")
        pr_url = pr.get("html_url")
        print(f"Created PR #{pr_number}: {pr_url}")
    except Exception as e:
        print("Failed to create PR:", e)
        sys.exit(8)

    auto = getenv("AUTO_MERGE")
    if auto and auto.lower() in ("1", "true", "yes"):
        # Additional safety: require an explicit allow flag or confirmation token
        allow = getenv("ALLOW_AUTO_MERGE") or getenv("MERGE_CONFIRM")
        if not allow or allow.lower() not in ("1", "true", "yes", "y", "ok", "confirm", "merge", "allowed"):
            print("AUTO_MERGE requested but no explicit allow flag set. Set ALLOW_AUTO_MERGE=true or MERGE_CONFIRM=yes to proceed with merging.")
            print("PR created but not merged for safety.")
            return
        try:
            print("Merging PR", pr_number)
            res = merge_pr(repo, pr_number, github_token)
            print("Merge result:", res)
        except Exception as e:
            print("Failed to merge PR:", e)
            sys.exit(9)


if __name__ == "__main__":
    main()
