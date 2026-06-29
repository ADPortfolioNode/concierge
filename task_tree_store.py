from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_available: Optional[bool] = None  # cached availability
_mem_store: Dict[str, Any] = {}  # fallback when Redis unavailable (shared with jobs/ version)


def get_redis() -> Optional[redis.Redis]:
    """Get a Redis client instance, reusing a single connection. Respects REDIS_ENABLED / USE_INLINE_TASKS.
    Returns None (with mem fallback) on connection failure instead of a broken client.
    """
    from config.settings import get_settings
    s = get_settings()
    if not getattr(s, 'redis_enabled', True) or getattr(s, 'use_inline_tasks', False):
        return None
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        if redis_url.lower() in ("none", "memory"):
            logger.info("Redis is explicitly disabled or set to in-memory. Returning None for Redis client.")
            _redis_available = False
            return None
        client = redis.from_url(
            redis_url, decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1
        )
        client.ping()  # validate
        _redis_client = client
        _redis_available = True
        return _redis_client
    except Exception:
        _redis_available = False
        logger.warning("Redis unavailable for task_tree_store, using in-memory fallback.")
        return None


def get_task_tree_key(thread_id: str) -> str:
    """Get the Redis key for a given task tree."""
    return f"task_tree:{thread_id}"


def get_task_update_channel(thread_id: str) -> str:
    """Get the Redis Pub/Sub channel name for a given thread."""
    return f"task_updates:{thread_id}"


def get_task_tree(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a task tree from Redis (with mem fallback). Never raises for status polling."""
    client = get_redis()
    if not client:
        raw = _mem_store.get(get_task_tree_key(thread_id))
        if raw is None:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw
    key = get_task_tree_key(thread_id)
    try:
        data = client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception:
        # fall back to mem on transient error
        raw = _mem_store.get(key)
        if raw is None:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw


def _find_node_in_tree(tree: Any, task_id: str) -> Optional[Dict[str, Any]]:
    """Recursively find a node in a task tree."""
    if not isinstance(tree, dict):
        return None
    if tree.get("task_id") == task_id:
        return tree
    for child in tree.get("children", []):
        found = _find_node_in_tree(child, task_id)
        if found:
            return found
    return None


def initialize_thread(thread_id: str, metadata: Dict[str, Any]):
    """Create the root of a new task tree in Redis (or mem fallback)."""
    tree = {
        "task_id": thread_id,
        "status": "running",
        "progress": 5,
        "children": [],
        "metadata": metadata,
    }
    client = get_redis()
    key = get_task_tree_key(thread_id)
    if not client:
        logger.warning(f"Cannot initialize thread {thread_id}, Redis is not available. Using mem fallback.")
        _mem_store[key] = json.dumps(tree)
        return
    try:
        client.set(key, json.dumps(tree))
        channel = get_task_update_channel(thread_id)
        client.publish(channel, json.dumps({"type": "init", "tree": tree}))
    except Exception:
        logger.warning(f"Redis write failed for init {thread_id}, falling back to mem.")
        _mem_store[key] = json.dumps(tree)


def _merge_node_update(existing_node: Dict[str, Any], kwargs: Dict[str, Any]) -> None:
    """Merge kwargs into an existing node, deep-merging metadata dicts."""
    if "metadata" in kwargs and isinstance(kwargs.get("metadata"), dict):
        merged_meta = {**(existing_node.get("metadata") or {}), **kwargs["metadata"]}
        kwargs = {**kwargs, "metadata": merged_meta}
    existing_node.update(kwargs)


_TERMINAL_STATUSES = {"done", "completed", "success", "error", "failed", "failure", "killed"}
_ACTIVE_STATUSES = {"running", "started", "thinking", "queued", "waiting", "pending"}


def _collect_descendants(node: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Return every descendant step node (excludes the node itself)."""
    descendants: list[Dict[str, Any]] = []
    for child in node.get("children") or []:
        descendants.append(child)
        descendants.extend(_collect_descendants(child))
    return descendants


def finalize_chat_thread(thread_id: str, summary: Optional[str] = None) -> None:
    """Mark a conversational assistant_thread root as complete."""
    import time as _time

    tree = get_task_tree(thread_id)
    if not tree:
        return
    children = tree.get("children") or []
    if children:
        return
    root_meta = dict(tree.get("metadata") or {})
    root_meta["end_time"] = _time.time()
    if summary:
        root_meta["result_summary"] = summary[:500]
    upsert_task_node(
        thread_id,
        thread_id,
        parent_id=None,
        status="done",
        progress=100,
        color="#22c55e",
        metadata=root_meta,
    )


def reconcile_idle_assistant_thread(thread_id: str) -> bool:
    """Close assistant_thread roots that have no workflow children."""
    tree = get_task_tree(thread_id)
    if not tree:
        return False
    children = tree.get("children") or []
    if children:
        return False
    meta = tree.get("metadata") or {}
    task_name = meta.get("task_name") or tree.get("task_name") or ""
    if task_name != "assistant_thread":
        return False
    if (tree.get("status") or "").lower() not in _ACTIVE_STATUSES:
        return False
    finalize_chat_thread(thread_id, summary="Chat session complete")
    return True


def reconcile_thread_with_celery(thread_id: str) -> bool:
    """Sync Redis step nodes with Celery result backend for stuck running steps."""
    import time as _time

    tree = get_task_tree(thread_id)
    if not tree:
        return False

    changed = False

    def _walk(node: Dict[str, Any], parent_id: Optional[str]) -> None:
        nonlocal changed
        node_id = node.get("task_id")
        if node_id and node_id != thread_id:
            status = (node.get("status") or "").lower()
            meta = node.get("metadata") or {}
            celery_id = meta.get("celery_task_id") if isinstance(meta, dict) else None
            if celery_id and status in _ACTIVE_STATUSES:
                try:
                    from celery.result import AsyncResult
                    from tasks.celery_app import celery_app

                    result = AsyncResult(celery_id, app=celery_app)
                    if result.ready():
                        if result.failed():
                            upsert_task_node(
                                thread_id,
                                node_id,
                                parent_id=parent_id or thread_id,
                                status="error",
                                progress=100,
                                color="#ef4444",
                                metadata={
                                    "result_summary": str(result.info),
                                    "end_time": _time.time(),
                                    "celery_task_id": celery_id,
                                },
                            )
                            changed = True
                        elif result.successful():
                            payload = result.result if isinstance(result.result, dict) else {}
                            summary = (
                                payload.get("summary")
                                or payload.get("output")
                                or str(result.result)[:500]
                            )
                            upsert_task_node(
                                thread_id,
                                node_id,
                                parent_id=parent_id or thread_id,
                                status="done",
                                progress=100,
                                color="#22c55e",
                                metadata={
                                    "result_summary": summary,
                                    "end_time": _time.time(),
                                    "celery_task_id": celery_id,
                                },
                            )
                            changed = True
                except Exception:
                    logger.warning(
                        "Failed to reconcile Celery state for %s/%s",
                        thread_id,
                        node_id,
                        exc_info=True,
                    )

        for child in node.get("children") or []:
            _walk(child, node_id or thread_id)

    _walk(tree, None)
    if changed:
        rollup_thread_status(thread_id)
    return changed


def reconcile_thread_status(thread_id: str) -> bool:
    """Full reconciliation: Celery sync, idle chat threads, then rollup."""
    changed = reconcile_thread_with_celery(thread_id)
    if reconcile_idle_assistant_thread(thread_id):
        changed = True
    else:
        rollup_thread_status(thread_id)
    return changed


def rollup_thread_status(thread_id: str) -> None:
    """Recompute root progress/status from all descendant steps (recursive)."""
    import time as _time

    tree = get_task_tree(thread_id)
    if not tree:
        return
    steps = _collect_descendants(tree)
    if not steps:
        return

    statuses = [(s.get("status") or "").lower() for s in steps]
    total = len(steps)
    progress = int(sum(int(s.get("progress") or 0) for s in steps) / total) if total else 0

    summaries = []
    for step in steps:
        meta = step.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("result_summary"):
            name = meta.get("task_name") or step.get("task_id") or "step"
            summaries.append(f"{name}: {meta.get('result_summary')}")

    root_meta = dict(tree.get("metadata") or {})
    root_meta["completed_steps"] = sum(
        1 for s in statuses if s in {"done", "completed", "success"}
    )
    root_meta["total_steps"] = total

    if all(s in _TERMINAL_STATUSES for s in statuses):
        if any(s in {"error", "failed", "failure"} for s in statuses):
            root_status = "error"
            color = "#ef4444"
        else:
            root_status = "done"
            color = "#22c55e"
        progress = 100
        root_meta["end_time"] = _time.time()
        if summaries:
            root_meta["result_summary"] = "\n\n".join(summaries[:5])
        upsert_task_node(
            thread_id,
            thread_id,
            parent_id=None,
            status=root_status,
            progress=progress,
            color=color,
            metadata=root_meta,
        )
    else:
        root_meta["last_update"] = _time.time()
        upsert_task_node(
            thread_id,
            thread_id,
            parent_id=None,
            status="running",
            progress=progress,
            metadata=root_meta,
        )


def upsert_task_node(thread_id: str, task_id: str, parent_id: Optional[str] = None, **kwargs):
    """Add or update a node in a task tree (redis or mem fallback)."""
    client = get_redis()
    key = get_task_tree_key(thread_id)
    if not client:
        # mem path (no lock)
        tree = get_task_tree(thread_id)
        if not tree:
            tree = {
                "task_id": thread_id,
                "status": "running",
                "progress": 5,
                "children": [],
                "metadata": {},
            }
            _mem_store[key] = json.dumps(tree)
        parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
        existing_node = _find_node_in_tree(tree, task_id)
        if existing_node:
            _merge_node_update(existing_node, kwargs)
        else:
            new_node = {"task_id": task_id, "children": [], **kwargs}
            parent_node.setdefault("children", []).append(new_node)
        _mem_store[key] = json.dumps(tree)
        return

    try:
        with client.lock(f"lock:{key}", timeout=5):
            tree = get_task_tree(thread_id)
            if not tree:
                logger.warning(f"Cannot upsert node for nonexistent thread_id: {thread_id}")
                return

            parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
            existing_node = _find_node_in_tree(tree, task_id)

            if existing_node:
                _merge_node_update(existing_node, kwargs)
            else:
                new_node = {"task_id": task_id, "children": [], **kwargs}
                parent_node.setdefault("children", []).append(new_node)

            client.set(key, json.dumps(tree))

        channel = get_task_update_channel(thread_id)
        update_payload = {"type": "node_update", "thread_id": thread_id, "task_id": task_id, **kwargs}
        client.publish(channel, json.dumps(update_payload))
    except Exception:
        logger.warning(f"Redis upsert failed for {thread_id}/{task_id}, using mem fallback.")
        tree = get_task_tree(thread_id) or {
            "task_id": thread_id,
            "status": "running",
            "progress": 5,
            "children": [],
            "metadata": {},
        }
        parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
        existing_node = _find_node_in_tree(tree, task_id)
        if existing_node:
            _merge_node_update(existing_node, kwargs)
        else:
            new_node = {"task_id": task_id, "children": [], **kwargs}
            parent_node.setdefault("children", []).append(new_node)
        _mem_store[key] = json.dumps(tree)


def append_task_logs(thread_id: str, task_id: str, log_lines: list[str]):
    """Append log lines to a task node."""
    upsert_task_node(thread_id, task_id, None, logs=log_lines)

def get_task_update_pubsub(thread_id: str):
    """Get a pubsub object for a given thread_id."""
    client = get_redis()
    if not client:
        return None
    try:
        pubsub = client.pubsub()
        pubsub.subscribe(get_task_update_channel(thread_id))
        return pubsub
    except Exception:
        return None
