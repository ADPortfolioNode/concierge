#!/usr/bin/env python3
"""Production product test for http://localhost:8002 — pages, links, APIs, media."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"

NAV_ROUTES = [
    ("/", "Home"),
    ("/goals", "Goals"),
    ("/strategy", "Strategy"),
    ("/tasks", "Tasks"),
    ("/workspace", "Workspace"),
    ("/media", "Media"),
    ("/howto", "Guide"),
    ("/capabilities", "Integrations"),
]

API_CHECKS = [
    ("GET", "/api/health/ready", None, lambda d: d.get("status") == "ok"),
    ("GET", "/api/v1/capabilities", None, lambda d: "plugins" in (d.get("data") or d)),
    ("GET", "/api/v1/plugins", None, lambda d: any(
        p.get("name") == "image_generation" for p in (d.get("data") or []) if isinstance(p, dict)
    )),
    ("GET", "/api/v1/concierge/media", None, lambda d: isinstance(d.get("data"), list) and len(d.get("data", [])) > 0),
    ("GET", "/api/v1/tasks", None, lambda d: "data" in d),
    ("GET", "/api/v1/concierge/conversation", None, lambda d: "data" in d),
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = dict(attrs)
        if tag == "a" and ad.get("href"):
            self.hrefs.append(ad["href"])
        if tag == "script" and ad.get("src"):
            self.scripts.append(ad["src"])


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")

    def warn(self, name: str, detail: str) -> None:
        self.warnings.append(f"{name}: {detail}")
        print(f"  WARN  {name} — {detail}")


def fetch(method: str, path: str, body: dict | None = None, timeout: int = 30) -> tuple[int, dict[str, str], bytes]:
    url = f"{BASE.rstrip('/')}{path}"
    hdrs = {"Accept": "application/json, text/html, */*"}
    data = None
    if body is not None:
        hdrs["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def test_spa_shell(r: Report) -> None:
    print("\n== 1. SPA shell & direct URL routes ==")
    for path, label in NAV_ROUTES:
        status, headers, body = fetch("GET", path)
        ctype = headers.get("Content-Type", "")
        if status == 404:
            r.fail(f"direct {path}", f"HTTP 404 — SPA fallback missing for {label}")
            continue
        if status != 200:
            r.fail(f"direct {path}", f"HTTP {status}")
            continue
        html = body.decode("utf-8", errors="replace")
        if "id=\"root\"" in html or '<div id="root">' in html or "Concierge" in html:
            r.ok(f"direct {path}", f"{label} shell ({ctype[:30]})")
        else:
            r.fail(f"direct {path}", "missing React root shell")


def test_static_assets(r: Report) -> None:
    print("\n== 2. Static assets from index.html ==")
    status, _, body = fetch("GET", "/")
    if status != 200:
        r.fail("index.html", f"HTTP {status}")
        return
    parser = LinkParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    scripts = [s for s in parser.scripts if s.startswith("/assets/")]
    if not scripts:
        r.fail("bundle scripts", "no /assets/*.js in index.html")
        return
    r.ok("bundle scripts", f"{len(scripts)} script(s)")
    for src in scripts[:3]:
        st, _, raw = fetch("GET", src)
        if st == 200 and len(raw) > 1000:
            r.ok(f"asset {src}", f"{len(raw)} bytes")
        else:
            r.fail(f"asset {src}", f"HTTP {st} size={len(raw)}")


def test_api_endpoints(r: Report) -> None:
    print("\n== 3. Production API endpoints ==")
    for method, path, body, check in API_CHECKS:
        try:
            status, _, raw = fetch(method, path, body)
            if status != 200:
                r.fail(path, f"HTTP {status}")
                continue
            data = json.loads(raw.decode())
            if check(data):
                detail = ""
                if path.endswith("/media"):
                    detail = f"{len(data.get('data', []))} items"
                elif path.endswith("/plugins"):
                    detail = f"{len(data.get('data', []))} plugins"
                r.ok(path, detail)
            else:
                r.fail(path, f"unexpected payload: {str(data)[:120]}")
        except Exception as exc:
            r.fail(path, str(exc))


def test_media_rendering(r: Report) -> None:
    print("\n== 4. Media generation & rendering ==")
    try:
        _, _, raw = fetch("GET", "/api/v1/concierge/media")
        data = json.loads(raw.decode())
        items = data.get("data") or []
        if not items:
            r.fail("media gallery", "no items")
            return
        r.ok("media gallery API", f"{len(items)} file(s)")
        # test newest 3 images
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if not url:
                continue
            st, hdrs, body = fetch("GET", url, timeout=15)
            ctype = hdrs.get("Content-Type", "")
            if st == 200 and len(body) > 0:
                kind = "full" if len(body) > 1000 else "thumb/placeholder"
                r.ok(f"render {url}", f"{len(body)} bytes {ctype[:20]} ({kind})")
            else:
                r.fail(f"render {url}", f"HTTP {st}")
    except Exception as exc:
        r.fail("media rendering", str(exc))


def test_image_plugin_job(r: Report) -> None:
    print("\n== 5. Image plugin job (quick accept) ==")
    try:
        status, _, raw = fetch(
            "POST",
            "/api/v1/jobs/run_plugin",
            {"plugin_name": "image_generation", "input_data": {"prompt": "product test: orange star"}},
        )
        if status != 200:
            r.fail("run_plugin POST", f"HTTP {status}")
            return
        data = json.loads(raw.decode())
        job_id = (data.get("data") or {}).get("job_id")
        if job_id:
            r.ok("run_plugin accepted", f"job {job_id[:12]}…")
        else:
            r.fail("run_plugin accepted", str(data)[:120])
    except Exception as exc:
        r.fail("run_plugin", str(exc))


def main() -> int:
    r = Report()
    print(f"Production product test @ {BASE}")

    test_spa_shell(r)
    test_static_assets(r)
    test_api_endpoints(r)
    test_media_rendering(r)
    test_image_plugin_job(r)

    print(f"\n== Summary: {r.passed} passed, {r.failed} failed, {len(r.warnings)} warnings ==")
    if r.warnings:
        print("\nWarnings:")
        for w in r.warnings:
            print(f"  - {w}")
    if r.errors:
        print("\nFailures:")
        for e in r.errors:
            print(f"  - {e}")
        return 1
    print("\nALL PRODUCTION PRODUCT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())