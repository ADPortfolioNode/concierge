#!/usr/bin/env python3
"""Diagnose stuck task trees in Redis."""
import json
import sys

from task_tree_store import get_redis, get_task_tree

IDS = [
    "fc45ab83-399",
    "df178467-086",
    "19d0dd84-090",
    "dd1b63ea-9a5",
    "e12fb337-7c5",
]


def walk(n, depth=0):
    ind = "  " * depth
    meta = n.get("metadata") or {}
    celery = (meta.get("celery_task_id") or "")[:12]
    print(
        f"{ind}{n.get('task_id')} status={n.get('status')} "
        f"prog={n.get('progress')} celery={celery}"
    )
    for c in n.get("children") or []:
        walk(c, depth + 1)


def main():
    client = get_redis()
    if not client:
        print("Redis unavailable")
        sys.exit(1)

    keys = list(client.scan_iter(match="task_tree:*", count=200))
    print(f"Total task_tree keys: {len(keys)}")
    print()

    for tid in IDS:
        tree = get_task_tree(tid)
        if not tree:
            print(f"=== {tid}: NOT FOUND ===\n")
            continue
        meta = tree.get("metadata") or {}
        print(
            f"=== {tid} root={tree.get('status')} prog={tree.get('progress')} "
            f"type={meta.get('task_type')} goal={str(meta.get('goal',''))[:60]} ==="
        )
        walk(tree)
        print()


if __name__ == "__main__":
    main()