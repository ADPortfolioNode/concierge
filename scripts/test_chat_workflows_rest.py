#!/usr/bin/env python3
"""RESTful chat workflow tests — mirrors the Concierge frontend HTTP flow.

Uses the same endpoints the browser calls:
  POST /api/v1/concierge/message   { message, history? }
  GET  /api/v1/concierge/timeline
  GET  /api/v1/concierge/conversation
  GET  /api/v1/tasks/{thread_id}/status

Usage:
  python scripts/test_chat_workflows_rest.py
  python scripts/test_chat_workflows_rest.py http://localhost:8002
  python scripts/test_chat_workflows_rest.py http://localhost:8002 --quick
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from _regression_env import bootstrap

bootstrap()

POLL_INTERVAL = 2
MAX_POLLS = 90  # ~3 min — matches frontend poll budget loosely


class Check:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  PASS  {name}{suffix}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def http_json(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    timeout: int = 120,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {raw[:400]}") from exc


def send_chat(
    base: str,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Same contract as conciergeService.sendMessage()."""
    payload: dict[str, Any] = {"message": message}
    if history:
        payload["history"] = history
    return http_json(base, "POST", "/api/v1/concierge/message", payload)


def extract_thread_id(resp: dict[str, Any]) -> str | None:
    data = resp.get("data") or {}
    raw = (data.get("meta") or {}).get("raw") or {}
    return (
        resp.get("thread_id")
        or data.get("thread_id")
        or raw.get("thread_id")
    )


def extract_assistant_content(resp: dict[str, Any]) -> str:
    data = resp.get("data") or {}
    return str(data.get("content") or data.get("response") or "")


def poll_task_tree(base: str, thread_id: str, checks: Check, label: str) -> dict[str, Any] | None:
    terminal = {"done", "completed", "success", "error", "failed", "failure", "unavailable"}
    last_status = ""
    for i in range(MAX_POLLS):
        tree = http_json(base, "GET", f"/api/v1/tasks/{thread_id}/status").get("data") or {}
        status = str(tree.get("status") or tree.get("state") or "").lower()
        last_status = status
        progress = tree.get("progress")
        if i % 5 == 0:
            print(f"    … poll {i + 1}/{MAX_POLLS} status={status} progress={progress}")
        if status in terminal:
            if status in ("done", "completed", "success"):
                checks.ok(label, f"thread {thread_id[:12]}… terminal={status}")
            elif status == "unavailable":
                checks.fail(label, "task tree unavailable (worker/redis down?)")
            else:
                meta = tree.get("metadata") or {}
                summary = str(meta.get("result_summary") or status)[:200]
                checks.fail(label, summary)
            return tree
        time.sleep(POLL_INTERVAL)
    checks.fail(label, f"poll timeout last_status={last_status}")
    return None


def flatten_tree_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Match frontend flattenWorkflowSteps — all nodes except synthetic root."""
    out: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], is_root: bool) -> None:
        if not is_root:
            out.append(node)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child, False)

    walk(tree, True)
    return out


def count_tree_steps(tree: dict[str, Any]) -> int:
    return len(flatten_tree_nodes(tree))


def step_names(tree: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for child in flatten_tree_nodes(tree):
        name = child.get("task_name") or (child.get("metadata") or {}).get("instructions") or child.get("task_id")
        names.append(str(name))
    return names


def timeline_task_count(base: str) -> tuple[int, list[str]]:
    plan = http_json(base, "GET", "/api/v1/concierge/timeline").get("data") or {}
    tasks = plan.get("tasks") or (plan.get("plan") or {}).get("tasks") or []
    if not isinstance(tasks, list):
        return 0, []
    titles = [str(t.get("title") or t.get("task_id") or "") for t in tasks if isinstance(t, dict)]
    return len(tasks), titles


def test_health(base: str, checks: Check) -> bool:
    print("\n== 0. API ready ==")
    try:
        resp = http_json(base, "GET", "/api/health/ready", timeout=15)
        if resp.get("status") == "ok" or "status" not in resp:
            checks.ok("health/ready")
            return True
        checks.fail("health/ready", str(resp)[:120])
    except Exception as exc:
        checks.fail("health/ready", str(exc))
    return False


def test_conversational_prompt(base: str, checks: Check) -> list[dict[str, str]]:
    print("\n== 1. Conversational chat (no background thread) ==")
    history: list[dict[str, str]] = []
    try:
        resp = send_chat(base, "Hello — what can you help me with?", history)
        content = extract_assistant_content(resp)
        thread_id = extract_thread_id(resp)
        raw = ((resp.get("data") or {}).get("meta") or {}).get("raw") or {}

        if thread_id and raw.get("status") == "processing":
            checks.fail("conversational no thread", f"unexpected workflow thread={thread_id[:12]}")
        elif len(content) < 8:
            checks.fail("conversational reply", f"too short: {content!r}")
        else:
            checks.ok("conversational reply", content[:80].replace("\n", " "))

        history.append({"role": "user", "content": "Hello — what can you help me with?"})
        history.append({"role": "assistant", "content": content})
        return history
    except Exception as exc:
        checks.fail("conversational chat", str(exc))
        return history


def test_status_query(base: str, checks: Check, history: list[dict[str, str]]) -> None:
    print("\n== 2. Status query (inline, like frontend dual-mode) ==")
    try:
        resp = send_chat(base, "What tasks are running?", history)
        content = extract_assistant_content(resp)
        if len(content) < 5:
            checks.fail("status query reply", content[:120])
        else:
            checks.ok("status query reply", content[:80].replace("\n", " "))
    except Exception as exc:
        checks.fail("status query", str(exc))


def test_logo_workflow(base: str, checks: Check, *, quick: bool) -> str | None:
    print("\n== 3. Logo workflow via chat (frontend POST flow) ==")
    prompt = "Create a minimalist logo for Concierge — 2 step workflow: prepare prompt then generate image"
    try:
        resp = send_chat(base, prompt)
        content = extract_assistant_content(resp)
        raw = ((resp.get("data") or {}).get("meta") or {}).get("raw") or {}
        thread_id = extract_thread_id(resp)

        if raw.get("status") == "processing" and thread_id:
            checks.ok("chat routed to workflow", f"thread={thread_id[:12]}…")
            if "started working" in content.lower() or len(content) > 10:
                checks.ok("processing acknowledgement", content[:60])
            else:
                checks.fail("processing acknowledgement", content[:120])

            if quick:
                checks.ok("logo workflow quick mode", "skipped long poll (--quick)")
                return thread_id

            tree = poll_task_tree(base, thread_id, checks, "logo workflow thread")
            if not tree:
                return thread_id

            steps = count_tree_steps(tree)
            names = step_names(tree)
            tl_count, tl_titles = timeline_task_count(base)

            if steps >= 2:
                checks.ok("workflow tree steps", f"{steps} nodes: {', '.join(n[:24] for n in names[:4])}")
            elif tl_count >= 2:
                checks.ok(
                    "planner 2-step workflow (timeline)",
                    f"{tl_count} tasks: {', '.join(t[:28] for t in tl_titles[:4])}",
                )
            elif steps == 1:
                checks.fail("planner 2-step workflow", f"tree={names}, timeline={tl_titles}")
            else:
                checks.fail("planner 2-step workflow", "no steps in tree or timeline")

            summary = str((tree.get("metadata") or {}).get("result_summary") or "")
            if "/media/images/" in summary:
                checks.ok("workflow result has media path", summary.split("/media/images/")[1][:40])
            elif "lm-unavailable" in summary.lower() or "unavailable" in summary.lower():
                checks.ok("workflow honest lm-unavailable", "no placeholder URL")
            return thread_id

        # Immediate reply path (conversational fallback)
        if content and raw.get("status") != "processing":
            checks.fail("logo workflow dispatch", f"got immediate reply: {content[:120]}")
        else:
            checks.fail("logo workflow dispatch", str(resp)[:200])
    except Exception as exc:
        checks.fail("logo workflow chat", str(exc))
    return None


def test_timeline_after_chat(base: str, checks: Check) -> None:
    print("\n== 4. Timeline introspection (frontend fetchTimeline) ==")
    try:
        plan = http_json(base, "GET", "/api/v1/concierge/timeline").get("data") or {}
        tasks = plan.get("tasks") or (plan.get("plan") or {}).get("tasks") or []
        if isinstance(tasks, list) and len(tasks) > 0:
            checks.ok("timeline has tasks", f"{len(tasks)} task(s)")
        else:
            checks.ok("timeline reachable", "empty plan (acceptable after idle)")
    except Exception as exc:
        checks.fail("timeline GET", str(exc))


def test_conversation_log(base: str, checks: Check) -> None:
    print("\n== 5. Conversation log (frontend fetchConversation) ==")
    try:
        msgs = http_json(base, "GET", "/api/v1/concierge/conversation").get("data") or []
        if isinstance(msgs, list) and len(msgs) >= 2:
            roles = {m.get("role") for m in msgs if isinstance(m, dict)}
            if "user" in roles or "assistant" in roles:
                checks.ok("conversation persisted", f"{len(msgs)} message(s)")
            else:
                checks.fail("conversation roles", str(roles))
        else:
            checks.ok("conversation endpoint", f"{len(msgs) if isinstance(msgs, list) else 0} message(s)")
    except Exception as exc:
        checks.fail("conversation GET", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="RESTful chat workflow tests (frontend parity)")
    parser.add_argument("base", nargs="?", default="http://localhost:8002")
    parser.add_argument("--quick", action="store_true", help="Skip long Celery poll")
    args = parser.parse_args()

    checks = Check()
    print(f"Chat workflow REST tests @ {args.base}")
    print("(same endpoints as artifacts/concierge conciergeService.ts)")

    if not test_health(args.base, checks):
        print("\n== Summary ==")
        print(f"  passed={checks.passed}  failed={checks.failed}")
        return 1

    history = test_conversational_prompt(args.base, checks)
    test_status_query(args.base, checks, history)
    test_logo_workflow(args.base, checks, quick=args.quick)
    test_timeline_after_chat(args.base, checks)
    test_conversation_log(args.base, checks)

    print("\n== Summary ==")
    print(f"  passed={checks.passed}  failed={checks.failed}")
    if checks.errors:
        print("\nFailures:")
        for err in checks.errors:
            print(f"  - {err}")
        return 1
    print("\nALL CHAT WORKFLOW REST TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())