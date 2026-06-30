#!/usr/bin/env python3
"""Generate test images via the production Concierge API."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"

PROMPTS = [
    "test image: minimalist concierge logo, flat vector blue and white",
    "test image: friendly robot mascot waving, cartoon style",
    "test image: sunset over mountains, warm orange sky",
    "test image: red apple on white background, product photo",
    "test image: abstract geometric pattern, purple and teal",
]


def post_json(path: str, body: dict) -> dict:
    url = f"{BASE.rstrip('/')}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_json(path: str) -> dict:
    url = f"{BASE.rstrip('/')}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def poll_job(job_id: str, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = get_json(f"/api/v1/jobs/{job_id}").get("data") or {}
        state = str(data.get("state") or data.get("status") or "").upper()
        if state in ("SUCCESS", "COMPLETED", "FAILURE", "FAILED"):
            return data
        time.sleep(2)
    raise TimeoutError(f"job {job_id} did not complete in {timeout}s")


def extract_result(data: dict) -> dict:
    result = data.get("result") or {}
    if isinstance(result, dict) and "result" in result:
        inner = result["result"]
        if isinstance(inner, dict):
            return inner
    return result if isinstance(result, dict) else {}


def main() -> int:
    print(f"Generating {len(PROMPTS)} test images @ {BASE}\n")
    generated: list[dict] = []

    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[{i}/{len(PROMPTS)}] {prompt[:60]}...")
        try:
            accepted = post_json(
                "/api/v1/jobs/run_plugin",
                {"plugin_name": "image_generation", "input_data": {"prompt": prompt}},
            )
            job_id = (accepted.get("data") or {}).get("job_id")
            if not job_id:
                print(f"  FAIL: no job_id — {accepted}")
                continue
            data = poll_job(job_id)
            state = str(data.get("state") or data.get("status") or "").upper()
            if state not in ("SUCCESS", "COMPLETED"):
                print(f"  FAIL: job state={state}")
                continue
            result = extract_result(data)
            url = result.get("url") or ""
            source = result.get("source") or "unknown"
            full_url = f"{BASE.rstrip('/')}{url}" if url.startswith("/") else url
            generated.append({"prompt": prompt, "url": url, "full_url": full_url, "source": source})
            print(f"  OK  {url}  (source={source})")
        except Exception as exc:
            print(f"  FAIL: {exc}")

    print(f"\n== Generated {len(generated)}/{len(PROMPTS)} images ==")
    for item in generated:
        print(f"  {item['full_url']}")
        print(f"    source: {item['source']}")
        print(f"    prompt: {item['prompt'][:70]}")

    # Media list
    try:
        media = get_json("/api/v1/concierge/media").get("data") or []
        if isinstance(media, list):
            print(f"\nMedia gallery: {len(media)} total item(s)")
    except Exception:
        pass

    return 0 if generated else 1


if __name__ == "__main__":
    sys.exit(main())