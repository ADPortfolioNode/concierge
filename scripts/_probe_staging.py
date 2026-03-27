#!/usr/bin/env python3
import requests

import os

URL_BASE = os.environ.get("VERCEL_ALIAS", "https://deoismconcierge-git-staging-adportfolionodes-projects.vercel.app")
TOKEN = os.environ.get("VERCEL_BYPASS_TOKEN")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
if TOKEN:
    headers["x-vercel-protection-bypass"] = TOKEN

def probe(path):
    url = URL_BASE.rstrip('/') + path
    print(f"REQUEST {url}")
    try:
        # Try header-based bypass first (if token present), otherwise try query-param
        r = requests.get(url, headers=headers, timeout=10)
        print("STATUS", r.status_code)
        text = r.text or ''
        print("BODY-SNIPPET:\n", text[:1000])
    except Exception as e:
        print("ERROR", repr(e))

if __name__ == '__main__':
    probe('/health')
    print('\n---\n')
    probe('/')
