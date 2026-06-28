from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Get a Redis client instance, reusing a single connection. Respects REDIS_ENABLED / USE_INLINE_TASKS."""
    from config.settings import get_settings
    s = get_settings()
    if not getattr(s, 'redis_enabled', True) or getattr(s, 'use_inline_tasks', False):
        return None
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        if redis_url.lower() in ("none", "memory"):
            logger.info("Redis is explicitly disabled or set to in-memory. Returning None for Redis client.")
            return None
        # Use a short timeout to prevent long delays if Redis is unavailable,
        # which is common in local --no-docker development.
        _redis_client = redis.from_url(
            redis_url, decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1
        )
    return _redis_client


def get_task_tree_key(thread_id: str) -> str:
    """Get the Redis key for a given task tree."""
    return f"task_tree:{thread_id}"


def get_task_update_channel(thread_id: str) -> str:
    """Get the Redis Pub/Sub channel name for a given thread."""
    return f"task_updates:{thread_id}"


def get_task_tree(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a task tree from Redis."""
    client = get_redis()
    if not client:
        return None
    key = get_task_tree_key(thread_id)
    data = client.get(key)
    if data:
        return json.loads(data)
    return None


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
    """Create the root of a new task tree in Redis."""
    tree = {
        "task_id": thread_id,
        "status": "running",
        "progress": 5,
        "children": [],
        "metadata": metadata,
    }
    client = get_redis()
    if not client:
        logger.warning(f"Cannot initialize thread {thread_id}, Redis is not available.")
        return
    key = get_task_tree_key(thread_id)
    client.set(key, json.dumps(tree))
    # Publish the initialization event
    channel = get_task_update_channel(thread_id)
    client.publish(channel, json.dumps({"type": "init", "tree": tree}))


def upsert_task_node(thread_id: str, task_id: str, parent_id: Optional[str], **kwargs):
    """Add or update a node in a task tree."""
    client = get_redis()
    if not client:
        logger.warning(f"Cannot upsert node for thread {thread_id}, Redis is not available.")
        return
    key = get_task_tree_key(thread_id)
    with client.lock(f"lock:{key}", timeout=5):
        tree = get_task_tree(thread_id)
        if not tree:
            logger.warning(f"Cannot upsert node for nonexistent thread_id: {thread_id}")
            return

        parent_node = _find_node_in_tree(tree, parent_id or thread_id) or tree
        existing_node = _find_node_in_tree(tree, task_id)

        if existing_node:
            existing_node.update(kwargs)
        else:
            new_node = {"task_id": task_id, "children": [], **kwargs}
            parent_node.setdefault("children", []).append(new_node)

        client.set(key, json.dumps(tree))

    # Publish the update event
    channel = get_task_update_channel(thread_id)
    update_payload = {"type": "node_update", "thread_id": thread_id, "task_id": task_id, **kwargs}
    client.publish(channel, json.dumps(update_payload))


def append_task_logs(thread_id: str, task_id: str, log_lines: list[str]):
    """Append log lines to a task node."""
    # This is a simplified version. A real implementation might use a separate Redis list.
    upsert_task_node(thread_id, task_id, None, logs=log_lines)

def get_task_update_pubsub(thread_id: str):
    """Get a pubsub object for a given thread_id."""
    client = get_redis()
    if not client:
        return None
    pubsub = client.pubsub()
    pubsub.subscribe(get_task_update_channel(thread_id))
    return pubsub
