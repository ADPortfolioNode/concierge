#!/usr/bin/env python3
"""Product test: Celery workflow metadata evolution over task lifecycle."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from typing import Any

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"
POLL_INTERVAL = 3
MAX_POLLS = 40


def http_json(method: str, path: str, body: dict | None = None) -> dict[str, Any]:
    url = f"{BASE.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def snapshot_tree(thread_id: str) -> dict[str, Any]:
    envelope = http_json("GET", f"/api/v1/tasks/{thread_id}/status")
    return envelope.get("data") or {}


def flatten_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], depth: int = 0) -> None:
        rows.append(
            {
                "depth": depth,
                "task_id": node.get("task_id"),
                "status": node.get("status"),
                "progress": node.get("progress"),
                "metadata_keys": sorted((node.get("metadata") or {}).keys()),
                "celery_task_id": (node.get("metadata") or {}).get("celery_task_id"),
                "has_summary": bool((node.get("metadata") or {}).get("result_summary")),
            }
        )
        for child in node.get("children") or []:
            walk(child, depth + 1)

    walk(tree)
    return rows


def main() -> int:
    goal = (
        "Create a 4-week sprint plan to launch a public REST API. "
        "Break it into research, design, implementation, and testing milestones."
    )
    print(f"==> Submitting agent job via {BASE}")
    accepted = http_json("POST", "/api/v1/jobs/run_agent", {"goal": goal, "context": "product test"})
    job_id = accepted["data"]["job_id"]
    print(f"    job_id={job_id}")

    thread_id: str | None = None
    job_states: list[str] = []
    tree_snapshots: list[dict[str, Any]] = []

    for i in range(MAX_POLLS):
        job = http_json("GET", f"/api/v1/jobs/{job_id}")
        job_data = job.get("data") or {}
        state = job_data.get("state") or job_data.get("status") or "unknown"
        job_states.append(state)

        result = job_data.get("result") or {}
        if isinstance(result, dict):
            thread_id = result.get("thread_id") or thread_id
            if not thread_id and isinstance(result.get("result"), dict):
                thread_id = result["result"].get("thread_id") or thread_id

        if thread_id:
            tree = snapshot_tree(thread_id)
            rows = flatten_nodes(tree)
            snap = {
                "poll": i,
                "elapsed_s": i * POLL_INTERVAL,
                "job_state": state,
                "root_status": tree.get("status"),
                "root_progress": tree.get("progress"),
                "child_count": len(rows) - 1,
                "nodes": rows,
            }
            tree_snapshots.append(snap)
            print(
                f"[{i:02d}] job={state:<9} root={tree.get('status'):<8} "
                f"progress={tree.get('progress')} children={len(rows)-1} "
                f"meta={snap['nodes'][0]['metadata_keys'] if rows else []}"
            )
            for row in rows[1:]:
                print(
                    f"      └ {row['task_id'][:12]}… status={row['status']} "
                    f"progress={row['progress']} celery={row['celery_task_id']}"
                )
        else:
            print(f"[{i:02d}] job={state:<9} (no thread_id yet)")

        terminal_job = state in ("SUCCESS", "FAILURE", "completed", "failed")
        terminal_tree = False
        if thread_id and tree_snapshots:
            root_status = (tree_snapshots[-1].get("root_status") or "").lower()
            terminal_tree = root_status in ("done", "completed", "error", "failed")
            if tree_snapshots[-1]["child_count"] > 0:
                child_done = all(
                    (n.get("status") or "").lower() in ("done", "completed", "error", "failed")
                    for n in tree_snapshots[-1]["nodes"][1:]
                )
                terminal_tree = terminal_tree and child_done

        if terminal_job and (not thread_id or terminal_tree):
            break
        time.sleep(POLL_INTERVAL)

    print("\n==> Summary")
    print(f"    job states seen: {' → '.join(dict.fromkeys(job_states))}")
    if thread_id:
        print(f"    thread_id: {thread_id}")
        print(f"    snapshots: {len(tree_snapshots)}")
        if tree_snapshots:
            first = tree_snapshots[0]
            last = tree_snapshots[-1]
            print(f"    metadata evolution: {first['nodes'][0]['metadata_keys']} → {last['nodes'][0]['metadata_keys']}")
            print(f"    children: {first['child_count']} → {last['child_count']}")
            progressed = last["child_count"] > first["child_count"] or last["root_progress"] != first["root_progress"]
            if progressed:
                print("    RESULT: PASS — metadata/tree evolved over workflow life")
                return 0
            print("    RESULT: FAIL — metadata frozen (no child nodes / no progress)")
            return 1
    print("    RESULT: FAIL — never received thread_id")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())