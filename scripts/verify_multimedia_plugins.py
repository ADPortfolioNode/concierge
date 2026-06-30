#!/usr/bin/env python3
"""Verify plugin registration, image generation, media API, and rendering URLs."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"


class R:
    def __init__(self) -> None:
        self.ok = 0
        self.failed = 0
        self.errs: list[str] = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.ok += 1
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.errs.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE.rstrip('/')}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, json.loads(resp.read().decode())


def post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE.rstrip('/')}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, json.loads(resp.read().decode())


def poll_job(job_id: str, timeout: int = 360) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, data = get(f"/api/v1/jobs/{job_id}")
        payload = data.get("data") or {}
        state = str(payload.get("state") or payload.get("status") or "").upper()
        if state in ("SUCCESS", "COMPLETED", "FAILURE", "FAILED"):
            return payload
        time.sleep(2)
    raise TimeoutError(job_id)


def image_bytes(path: str) -> tuple[int, int]:
    req = urllib.request.Request(f"{BASE.rstrip('/')}{path}", headers={"Accept": "image/*"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return resp.status, len(body)


def main() -> int:
    r = R()
    print(f"Multimedia plugin verification @ {BASE}\n")

    print("== 1. Plugin registry ==")
    try:
        _, body = get("/api/v1/plugins")
        plugins = body.get("data") or []
        names = {p.get("name") for p in plugins if isinstance(p, dict)}
        if "image_generation" in names:
            r.pass_("plugins list", f"image_generation registered ({len(plugins)} plugins)")
        else:
            r.fail("plugins list", f"missing image_generation; got {names}")
    except Exception as exc:
        r.fail("plugins list", str(exc))

    print("\n== 2. Capabilities ==")
    try:
        _, body = get("/api/v1/capabilities")
        data = body.get("data") or {}
        plugin_names = [p.get("name") for p in (data.get("plugins") or []) if isinstance(p, dict)]
        if "image_generation" in plugin_names:
            r.pass_("capabilities plugins", f"{len(plugin_names)} plugin(s)")
        else:
            r.fail("capabilities plugins", str(plugin_names))
    except Exception as exc:
        r.fail("capabilities", str(exc))

    print("\n== 3. Image plugin job (Celery) ==")
    image_url = ""
    try:
        _, accepted = post(
            "/api/v1/jobs/run_plugin",
            {"plugin_name": "image_generation", "input_data": {"prompt": "verify: blue circle icon"}},
        )
        job_id = (accepted.get("data") or {}).get("job_id")
        if not job_id:
            r.fail("run_plugin accepted", str(accepted)[:200])
        else:
            result = poll_job(job_id)
            state = str(result.get("state") or result.get("status") or "").upper()
            if state not in ("SUCCESS", "COMPLETED"):
                r.fail("plugin job", f"state={state}")
            else:
                payload = result.get("result") or {}
                if isinstance(payload, dict) and "result" in payload:
                    payload = payload["result"]
                image_url = (payload or {}).get("url") if isinstance(payload, dict) else ""
                source = (payload or {}).get("source", "?") if isinstance(payload, dict) else "?"
                if image_url:
                    r.pass_("plugin job result", f"url={image_url} source={source}")
                else:
                    r.fail("plugin job result", str(payload)[:200])
    except Exception as exc:
        r.fail("plugin job", str(exc))

    print("\n== 4. Media list API ==")
    try:
        _, body = get("/api/v1/concierge/media")
        items = body.get("data") or []
        if isinstance(items, list) and len(items) > 0:
            r.pass_("media list", f"{len(items)} file(s)")
            newest = items[0]
            if isinstance(newest, dict) and newest.get("url"):
                r.pass_("media list newest", newest.get("url", ""))
            else:
                r.fail("media list newest", "missing url")
        else:
            r.fail("media list", "empty")
    except Exception as exc:
        r.fail("media list", str(exc))

    print("\n== 5. Image URL rendering (HTTP serve) ==")
    try:
        test_url = image_url
        if not test_url:
            _, body = get("/api/v1/concierge/media")
            items = body.get("data") or []
            if items and isinstance(items[0], dict):
                test_url = items[0].get("url", "")
        if not test_url:
            r.fail("image serve", "no url to test")
        else:
            status, size = image_bytes(test_url)
            if status == 200 and size > 0:
                kind = "full image" if size > 1000 else "tiny/placeholder"
                r.pass_("image serve", f"{test_url} ({size} bytes, {kind})")
            else:
                r.fail("image serve", f"status={status} size={size}")
    except Exception as exc:
        r.fail("image serve", str(exc))

    print("\n== 6. In-process plugin smoke ==")
    try:
        import asyncio
        from plugins.image_generation_plugin import ImageGenerationPlugin

        out = asyncio.run(ImageGenerationPlugin().run("verify smoke: green leaf"))
        url = out.get("url") if isinstance(out, dict) else ""
        if url:
            r.pass_("plugin.run direct", f"source={out.get('source', '?')}")
        else:
            r.fail("plugin.run direct", str(out)[:200])
    except Exception as exc:
        r.fail("plugin.run direct", str(exc))

    print(f"\n== Summary: {r.ok} passed, {r.failed} failed ==")
    if r.errs:
        for e in r.errs:
            print(f"  - {e}")
        return 1
    print("ALL MULTIMEDIA PLUGIN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())