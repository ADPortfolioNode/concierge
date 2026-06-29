#!/usr/bin/env python3
"""One-time (or periodic) reconciliation of stale Redis task trees with Celery."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_tree_store import get_redis, get_task_tree, reconcile_thread_status


def main() -> int:
    client = get_redis()
    if not client:
        print("Redis unavailable")
        return 1

    keys = list(client.scan_iter(match="task_tree:*", count=500))
    print(f"Scanning {len(keys)} task trees...\n")

    changed = 0
    for key in keys:
        thread_id = key.split(":", 1)[1] if ":" in key else key
        before = get_task_tree(thread_id)
        if not before:
            continue
        before_status = before.get("status")
        reconcile_thread_status(thread_id)
        after_status = (get_task_tree(thread_id) or {}).get("status")
        if after_status != before_status:
            changed += 1
            print(f"  {thread_id[:12]}… {before_status} -> {after_status}")

    print(f"\nReconciled {changed} task tree(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())