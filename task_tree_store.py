from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_available: Optional[bool] = None  # None = untested
_mem_store: Dict[str, Any] = {}          # in-memory fallback when Redis is unavailable


def get_redis() -> Optional[redis.Redis]:
    """Return a Redis client, or None if Redis is unavailable (cached per process)."""
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        _redis_available = True
        return _redis_client
    except Exception:
        _redis_available = False
        return None


def get_task_tree_key(thread_id: str) -> str:
    return f"task_tree:{thread_id}"


def get_task_update_channel(thread_id: str) -> str:
    return f"task_updates:{thread_id}"


def get_task_tree(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a task tree from Redis or in-memory fallback."""
    key = get_task_tree_key(thread_id)
    r = get_redis()
    if r is None:
        raw = _mem_store.get(key)
        if raw is None:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw
    try:
        data = r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception:
        return None


def _find_node_in_tree(tree: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    if tree.get("task_id") == task_id:
        return tree
    for child in tree.get("children", []):
        found = _find_node_in_tree(child, task_id)
        if found:
            return found
    return None


def initialize_thread(thread_id: str, metadata: Dict[str, Any]):
    """Create the root of a new task tree (Redis or in-memory fallback)."""
    tree = {
        "task_id": thread_id,
        "status": "running",
        "progress": 5,
        "children": [],
        "metadata": metadata,
    }
    key = get_task_tree_key(thread_id)
    serialized = json.dumps(tree)
    r = get_redis()
    if r is None:
        _mem_store[key] = serialized
        return
    try:
        r.set(key, serialized)
        channel = get_task_update_channel(thread_id)
        r.publish(channel, json.dumps({"type": "init", "tree": tree}))
    except Exception:
        _mem_store[key] = serialized


def upsert_task_node(thread_id: str, task_id: str, parent_id: Optional[str], **kwargs):
    """Add or update a node in a task tree (Redis or in-memory fallback)."""
    key = get_task_tree_key(thread_id)
    r = get_redis()

    if r is None:
        tree = get_task_tree(thread_id)
        if not tree:
            logger.warning("Cannot upsert node for nonexistent thread_id: %s", thread_id)
            return
        parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
        existing_node = _find_node_in_tree(tree, task_id)
        if existing_node:
            existing_node.update(kwargs)
        else:
            new_node = {"task_id": task_id, "children": [], **kwargs}
            parent_node.setdefault("children", []).append(new_node)
        _mem_store[key] = json.dumps(tree)
        return

    try:
        with r.lock(f"lock:{key}", timeout=5):
            tree = get_task_tree(thread_id)
            if not tree:
                logger.warning("Cannot upsert node for nonexistent thread_id: %s", thread_id)
                return
            parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
            existing_node = _find_node_in_tree(tree, task_id)
            if existing_node:
                existing_node.update(kwargs)
            else:
                new_node = {"task_id": task_id, "children": [], **kwargs}
                parent_node.setdefault("children", []).append(new_node)
            r.set(key, json.dumps(tree))
        channel = get_task_update_channel(thread_id)
        update_payload = {"type": "node_update", "thread_id": thread_id, "task_id": task_id, **kwargs}
        r.publish(channel, json.dumps(update_payload))
    except Exception:
        tree = get_task_tree(thread_id)
        if tree:
            parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
            existing_node = _find_node_in_tree(tree, task_id)
            if existing_node:
                existing_node.update(kwargs)
            else:
                new_node = {"task_id": task_id, "children": [], **kwargs}
                parent_node.setdefault("children", []).append(new_node)
            _mem_store[key] = json.dumps(tree)


def append_task_logs(thread_id: str, task_id: str, log_lines: list):
    """Append log lines to a task node."""
    upsert_task_node(thread_id, task_id, None, logs=log_lines)


def get_task_update_pubsub(thread_id: str):
    """Get a pubsub object for a given thread_id (returns None if Redis unavailable)."""
    r = get_redis()
    if r is None:
        return None
    try:
        pubsub = r.pubsub()
        pubsub.subscribe(get_task_update_channel(thread_id))
        return pubsub
    except Exception:
        return None
