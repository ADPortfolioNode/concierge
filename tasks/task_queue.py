"""Async in-memory task queue with status tracking.

The queue is backed by an ``asyncio.Queue``. A worker coroutine polls for
tasks and dispatches them to registered handlers. Results and status are
kept in an in-memory dict keyed by task ID (fast poll endpoint).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional

from .task_model import Task, TaskStatus

logger = logging.getLogger(__name__)

# Type alias for async task handlers
TaskHandler = Callable[[Task], Coroutine[Any, Any, Any]]


class TaskQueue:
    """Thread-safe asyncio task queue with handler registry and status tracking."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, TaskHandler] = {}
        self._lock = threading.RLock()
        self._worker_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """Register an async *handler* for *task_type*."""
        with self._lock:
            self._handlers[task_type] = handler
        logger.info("TaskQueue: registered handler for %r", task_type)

    # ------------------------------------------------------------------
    # Enqueue / lookup
    # ------------------------------------------------------------------

    def enqueue(self, task: Task) -> Task:
        """Add *task* to the queue. Returns the task (with assigned ID)."""
        with self._lock:
            self._tasks[task.id] = task
        self._queue.put_nowait(task)
        logger.info("TaskQueue: enqueued task %s (type=%s)", task.id, task.type)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[Task]:
        with self._lock:
            return list(self._tasks.values())

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    async def start_worker(self) -> None:
        """Start the background worker coroutine (call once at app startup)."""
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("TaskQueue worker started.")

    async def _worker_loop(self) -> None:
        while True:
            try:
                task: Task = await self._queue.get()
                await self._process(task)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("TaskQueue worker loop error")

    async def _process(self, task: Task) -> None:
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat() + "Z"

        handler = self._handlers.get(task.type)
        if handler is None:
            logger.warning("No handler registered for task type %r", task.type)
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = f"No handler registered for task type {task.type!r}"
                task.completed_at = datetime.utcnow().isoformat() + "Z"
            return

        try:
            result = await handler(task)
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.utcnow().isoformat() + "Z"
            logger.info("TaskQueue: completed task %s", task.id)
        except Exception as exc:
            logger.exception("TaskQueue: task %s failed", task.id)
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_QUEUE: Optional[TaskQueue] = None


def get_queue() -> TaskQueue:
    """Return the module-level singleton TaskQueue, creating it if needed."""
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = TaskQueue()
    return _QUEUE
