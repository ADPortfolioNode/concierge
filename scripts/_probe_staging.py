#!/usr/bin/env python3
import requests

URL_BASE = "https://deoismconcierge-git-staging-adportfolionodes-projects.vercel.app"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def probe(path):
    url = URL_BASE.rstrip('/') + path
    print(f"REQUEST {url}")
    try:
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
