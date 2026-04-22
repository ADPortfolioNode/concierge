from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import redis

DEFAULT_REDIS_URL = 'redis://redis:6379/1'
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('CELERY_RESULT_BACKEND') or DEFAULT_REDIS_URL

_redis_client: Optional[redis.Redis] = None


def _build_redis_client(url: str) -> redis.Redis:
    client = redis.from_url(url, decode_responses=True)
    client.ping()
    return client


def _resolve_redis_url(url: str) -> str:
    if url == DEFAULT_REDIS_URL:
        local_url = url.replace('redis://redis:6379', 'redis://127.0.0.1:6379')
        try:
            _build_redis_client(local_url)
            return local_url
        except Exception:
            pass
    return url


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        resolved_url = _resolve_redis_url(REDIS_URL)
        _redis_client = redis.from_url(resolved_url, decode_responses=True)
    return _redis_client


def _make_key(thread_id: str) -> str:
    return f'task_tree:{thread_id}'


def _find_node(node: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    if node.get('task_id') == task_id:
        return node
    for child in node.get('children', []):
        found = _find_node(child, task_id)
        if found is not None:
            return found
    return None


def _ensure_tree(tree: Dict[str, Any]) -> Dict[str, Any]:
    if 'children' not in tree or tree['children'] is None:
        tree['children'] = []
    return tree


def get_task_tree(thread_id: str) -> Optional[Dict[str, Any]]:
    data = get_redis().get(_make_key(thread_id))
    if not data:
        return None
    try:
        tree = json.loads(data)
        return tree
    except Exception:
        return None


def _save_task_tree(thread_id: str, tree: Dict[str, Any]) -> None:
    get_redis().set(_make_key(thread_id), json.dumps(tree))


def initialize_thread(thread_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    metadata = metadata or {}
    root = {
        'task_id': thread_id,
        'parent_id': None,
        'task_name': metadata.get('task_name', 'assistant_thread'),
        'status': 'running',
        'state': 'PROGRESS',
        'progress': 0,
        'color': metadata.get('color', '#7c6af7'),
        'metadata': {
            'start_time': metadata.get('start_time', time.time()),
            'logs': [],
            'result_summary': None,
            **{k: v for k, v in (metadata or {}).items() if k not in {'task_name', 'color', 'start_time', 'logs', 'result_summary'}}
        },
        'children': [],
    }
    _save_task_tree(thread_id, root)


def upsert_task_node(
    thread_id: str,
    task_id: str,
    parent_id: Optional[str] = None,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    color: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    children: Optional[List[str]] = None,
) -> None:
    if not thread_id or not task_id:
        return

    tree = get_task_tree(thread_id)
    if tree is None:
        initialize_thread(thread_id, {'task_name': 'assistant_thread'})
        tree = get_task_tree(thread_id)
    if tree is None:
        return

    node = _find_node(tree, task_id)
    if node is None:
        node = {
            'task_id': task_id,
            'parent_id': parent_id,
            'task_name': (metadata or {}).get('task_name') or task_id,
            'status': status or 'waiting',
            'state': 'PROGRESS',
            'progress': progress if progress is not None else 0,
            'color': color or '#7c6af7',
            'metadata': {
                'start_time': time.time(),
                'logs': [],
                'result_summary': None,
                **{k: v for k, v in (metadata or {}).items() if k not in {'task_name', 'start_time', 'logs', 'result_summary'}},
            },
            'children': [],
        }
        parent = _find_node(tree, parent_id) if parent_id else tree
        if parent is None:
            parent = tree
        if 'children' not in parent or parent['children'] is None:
            parent['children'] = []
        parent['children'].append(node)
    else:
        if status is not None:
            node['status'] = status
        if progress is not None:
            node['progress'] = progress
        if color is not None:
            node['color'] = color
        if metadata is not None:
            node_meta = node.get('metadata') or {}
            node_meta.update(metadata)
            node['metadata'] = node_meta
    if children is not None:
        node['children'] = [{'task_id': cid, 'parent_id': task_id, 'task_name': cid, 'status': 'waiting', 'state': 'PROGRESS', 'progress': 0, 'color': '#7c6af7', 'metadata': {'start_time': time.time(), 'logs': [], 'result_summary': None}, 'children': []} for cid in children]
    _save_task_tree(thread_id, tree)


def append_task_logs(thread_id: str, task_id: str, log_entry: str) -> None:
    tree = get_task_tree(thread_id)
    if tree is None:
        return
    node = _find_node(tree, task_id)
    if node is None:
        return
    node_meta = node.get('metadata') or {}
    logs = node_meta.get('logs') or []
    logs.append({'timestamp': time.time(), 'entry': log_entry})
    node_meta['logs'] = logs
    node['metadata'] = node_meta
    _save_task_tree(thread_id, tree)


def clear_task_tree(thread_id: str) -> None:
    get_redis().delete(_make_key(thread_id))
