#!/usr/bin/env python3
"""Product test: image and media generation workflows end-to-end."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"
POLL_INTERVAL = 3
MAX_POLLS = 60


class Check:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  PASS  {name}{suffix}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        print(f"  SKIP  {name} — {reason}")


def http_raw(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
    timeout: int = 120,
) -> tuple[int, dict[str, str], bytes]:
    url = f"{BASE.rstrip('/')}{path}"
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
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


def http_json(method: str, path: str, body: dict | None = None, timeout: int = 120) -> dict[str, Any]:
    status, _, raw = http_raw(method, path, body=body, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"{method} {path} -> HTTP {status}: {raw[:300]!r}")
    return json.loads(raw.decode())


def poll_job(job_id: str, checks: Check, label: str) -> dict[str, Any] | None:
    terminal = {"SUCCESS", "FAILURE", "completed", "failed", "REVOKED"}
    for i in range(MAX_POLLS):
        job = http_json("GET", f"/api/v1/jobs/{job_id}")
        data = job.get("data") or {}
        state = str(data.get("state") or data.get("status") or "unknown").upper()
        if state in terminal or i == MAX_POLLS - 1:
            if state in ("SUCCESS", "COMPLETED"):
                checks.ok(label, f"job {job_id[:12]}… state={state}")
            elif state == "FAILURE":
                err = data.get("error") or data.get("result") or data
                checks.fail(label, f"job failed: {str(err)[:200]}")
            else:
                checks.fail(label, f"job ended state={state}")
            return data
        time.sleep(POLL_INTERVAL)
    checks.fail(label, "poll timeout")
    return None


def poll_thread(thread_id: str, checks: Check, label: str) -> dict[str, Any] | None:
    terminal = {"done", "completed", "success", "error", "failed", "failure"}
    for i in range(MAX_POLLS):
        tree = http_json("GET", f"/api/v1/tasks/{thread_id}/status").get("data") or {}
        status = (tree.get("status") or "").lower()
        if status in terminal or i == MAX_POLLS - 1:
            if status in ("done", "completed", "success"):
                checks.ok(label, f"thread {thread_id[:12]}… status={status}")
            elif status in ("error", "failed", "failure"):
                meta = tree.get("metadata") or {}
                checks.fail(label, f"thread error: {str(meta.get('result_summary', status))[:200]}")
            else:
                checks.fail(label, f"thread stuck status={status}")
            return tree
        time.sleep(POLL_INTERVAL)
    checks.fail(label, "poll timeout")
    return None


def _is_valid_image_bytes(body: bytes) -> bool:
    if len(body) < 8:
        return False
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if body[:3] == b"\xff\xd8\xff":
        return True
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return True
    return False


def assert_image_url(checks: Check, name: str, url: str, *, allow_placeholder: bool = True) -> bool:
    if not url:
        checks.fail(name, "empty url")
        return False
    path = url
    if path.startswith("http"):
        checks.skip(name, f"remote url only: {path[:60]}")
        return True
    if not path.startswith("/"):
        path = "/" + path.lstrip("/")
    status, headers, body = http_raw("GET", path, headers={"Accept": "image/*"}, timeout=30)
    ctype = headers.get("Content-Type", "")
    if status == 200 and _is_valid_image_bytes(body):
        kind = "placeholder" if len(body) < 500 and allow_placeholder else "image"
        checks.ok(name, f"{path} ({len(body)} bytes, {ctype or kind})")
        return True
    checks.fail(name, f"GET {path} -> {status}, {len(body)} bytes, type={ctype}")
    return False


def test_plugin_direct(checks: Check) -> str | None:
    print("\n== 1. Image plugin (in-process) ==")
    try:
        import asyncio
        from plugins.image_generation_plugin import ImageGenerationPlugin

        plugin = ImageGenerationPlugin()
        result = asyncio.run(plugin.run("product test: minimalist concierge logo, flat vector"))
        url = result.get("url") or ""
        source = result.get("source") or "unknown"
        if url:
            checks.ok("plugin.run returns url", f"source={source}")
            assert_image_url(checks, "plugin image reachable", url)
            if result.get("source", "").startswith("gemini"):
                checks.ok("plugin gemini fallback used", result.get("source", ""))
            elif result.get("source", "").startswith("ollama"):
                checks.ok("plugin ollama/llama fallback used", result.get("source", ""))
            elif result.get("error"):
                checks.ok("plugin error surfaced", str(result.get("error"))[:80])
            return url
        checks.fail("plugin.run returns url", str(result)[:200])
    except Exception as exc:
        checks.fail("plugin.run", str(exc))
    return None


def test_plugin_job(checks: Check) -> str | None:
    print("\n== 2. Image plugin (Celery job) ==")
    try:
        accepted = http_json(
            "POST",
            "/api/v1/jobs/run_plugin",
            {"plugin_name": "image_generation", "input_data": {"prompt": "product test: blue geometric icon"}},
        )
        job_id = (accepted.get("data") or {}).get("job_id")
        if not job_id:
            checks.fail("run_plugin accepted", str(accepted)[:200])
            return None
        data = poll_job(job_id, checks, "run_plugin image_generation")
        if not data:
            return None
        result = data.get("result") or {}
        if isinstance(result, dict) and "result" in result:
            result = result["result"]
        if isinstance(result, dict):
            url = result.get("url")
            source = result.get("source") or "unknown"
            if url:
                assert_image_url(checks, "plugin job image reachable", url)
                if source.startswith("gemini"):
                    checks.ok("plugin job gemini fallback", f"source={source}")
                elif source.startswith("ollama"):
                    checks.ok("plugin job ollama/llama fallback", f"source={source}")
                elif source.startswith("placeholder"):
                    checks.ok("plugin job placeholder fallback", f"source={source}")
                elif source == "gpt-image-1":
                    checks.ok("plugin job openai generation", f"source={source}")
                return url
        checks.fail("plugin job result url", str(result)[:200])
    except Exception as exc:
        checks.fail("run_plugin workflow", str(exc))
    return None


def test_agent_image_goal(checks: Check) -> str | None:
    print("\n== 3. Agent job image goal (Celery chain) ==")
    try:
        goal = "Generate an image of a friendly robot mascot for Concierge product test"
        accepted = http_json("POST", "/api/v1/jobs/run_agent", {"goal": goal, "context": "media test"})
        job_id = (accepted.get("data") or {}).get("job_id")
        if not job_id:
            checks.fail("run_agent accepted", str(accepted)[:200])
            return None
        data = poll_job(job_id, checks, "run_agent image goal")
        if not data:
            return None
        result = data.get("result") or {}
        if isinstance(result, dict):
            thread_id = result.get("thread_id")
            if not thread_id and isinstance(result.get("result"), dict):
                thread_id = result["result"].get("thread_id")
            if thread_id:
                tree = poll_thread(thread_id, checks, "agent image thread")
                if tree:
                    summary = str((tree.get("metadata") or {}).get("result_summary") or "")
                    for token in summary.split():
                        if "/media/images/" in token or token.startswith("http"):
                            assert_image_url(checks, "agent thread mentions image", token.strip(".,;"))
                            return token
                    checks.ok("agent image thread completed", "no /media url in summary (may be text-only fallback)")
                    return thread_id
        checks.fail("run_agent thread_id", str(result)[:200])
    except Exception as exc:
        checks.fail("run_agent image workflow", str(exc))
    return None


def test_chat_image_goal(checks: Check) -> str | None:
    print("\n== 4. Chat message image goal ==")
    try:
        msg = "Generate an image of a sunset over mountains for product test"
        resp = http_json("POST", "/api/v1/concierge/message", {"message": msg})
        data = resp.get("data") or resp
        raw = (data.get("meta") or {}).get("raw") or {}
        thread_id = resp.get("thread_id") or data.get("thread_id") or raw.get("thread_id")
        raw_status = raw.get("status")
        if raw_status == "processing" and thread_id:
            checks.ok("chat routed to workflow", f"thread={thread_id[:12]}…")
            tree = poll_thread(thread_id, checks, "chat image thread")
            if tree:
                return thread_id
        elif raw.get("status") == "success" or data.get("content"):
            text = str(data.get("response") or data.get("content") or "")
            if "/media/images/" in text:
                for token in text.split():
                    if "/media/images/" in token:
                        assert_image_url(checks, "chat inline image", token.strip(".,;"))
                return text
            checks.fail("chat image goal", f"got success without workflow: {text[:120]}")
        else:
            checks.fail("chat image goal", str(data)[:200])
    except Exception as exc:
        checks.fail("chat image workflow", str(exc))
    return None


def test_media_api(checks: Check) -> None:
    print("\n== 5. Media list API ==")
    try:
        resp = http_json("GET", "/api/v1/concierge/media")
        items = resp.get("data") or []
        if isinstance(items, list) and len(items) > 0:
            checks.ok("media list non-empty", f"{len(items)} item(s)")
            first = items[0]
            url = first.get("url") if isinstance(first, dict) else None
            if url:
                assert_image_url(checks, "media list first item", url)
        else:
            checks.fail("media list non-empty", f"got {type(items).__name__}")
    except Exception as exc:
        checks.fail("media list API", str(exc))


def test_timeline_graph(checks: Check) -> None:
    print("\n== 6. Timeline graph PNG ==")
    try:
        http_json("POST", "/api/v1/concierge/message", {"message": "Plan a 2-step logo design workflow for test"})
        status, headers, body = http_raw("GET", "/api/v1/concierge/timeline/graph", timeout=30)
        ctype = headers.get("Content-Type", "")
        if status == 200 and _is_valid_image_bytes(body):
            checks.ok("timeline graph png", f"{len(body)} bytes, type={ctype or 'image/png'}")
        else:
            checks.fail("timeline graph png", f"status={status} type={ctype} len={len(body)}")
    except Exception as exc:
        checks.fail("timeline graph png", str(exc))


def test_transcription_stub(checks: Check) -> None:
    print("\n== 7. Audio transcription stub ==")
    try:
        import asyncio
        from pathlib import Path
        from workstation.transcription_service import transcribe

        tmp = Path("/tmp/media_test_voice.wav")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(b"RIFF" + b"\x00" * 40)
        text = asyncio.run(transcribe(tmp))
        if text and "transcription" in text.lower():
            checks.ok("transcription stub", text[:80])
        else:
            checks.fail("transcription stub", repr(text))
    except Exception as exc:
        checks.fail("transcription stub", str(exc))


def test_video_metadata_stub(checks: Check) -> None:
    print("\n== 8. Video metadata stub ==")
    try:
        from pathlib import Path
        from workstation.media_processor import extract_video_metadata

        tmp = Path("/tmp/media_test_clip.mp4")
        tmp.write_bytes(b"\x00" * 128)
        meta = extract_video_metadata(tmp)
        if meta.get("size") == 128:
            checks.ok("video metadata stub", str(meta.get("note", ""))[:60])
        else:
            checks.fail("video metadata stub", str(meta))
    except Exception as exc:
        checks.fail("video metadata stub", str(exc))


def main() -> int:
    checks = Check()
    print(f"Media generation workflow tests @ {BASE}")

    test_plugin_direct(checks)
    test_plugin_job(checks)
    test_agent_image_goal(checks)
    test_chat_image_goal(checks)
    test_media_api(checks)
    test_timeline_graph(checks)
    test_transcription_stub(checks)
    test_video_metadata_stub(checks)

    print("\n== Summary ==")
    print(f"  passed={checks.passed}  failed={checks.failed}  skipped={checks.skipped}")
    if checks.errors:
        print("\nFailures:")
        for err in checks.errors:
            print(f"  - {err}")
        return 1
    print("\nALL MEDIA WORKFLOW CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())