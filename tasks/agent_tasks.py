"""Celery tasks that delegate to the agent orchestration layer.

Each task runs a SacredTimeline pass for the supplied goal and context,
returning an ApiResponse-compatible dict that the job router serialises
back to the HTTP caller.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_sync(coro) -> Any:
    """Run an async coroutine from a synchronous Celery worker thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running loop in this thread — create a fresh one.
        return asyncio.run(coro)


@celery_app.task(bind=True, name="tasks.agent_tasks.run_agent_task")
def run_agent_task(self, context: str, goal: str) -> Dict[str, Any]:
    """Run the sacred timeline for a given *goal* with optional *context*.

    Returns a dict with ``status``, ``result`` (the agent response), and
    ``task_id`` so callers can correlate polling responses.
    """
    task_id = self.request.id
    logger.info("run_agent_task[%s] goal=%r", task_id, goal[:80])

    async def _execute():
        from memory.memory_store import MemoryStore
        from core.concurrency import AsyncConcurrencyManager
        from orchestration.sacred_timeline import SacredTimeline

        memory = MemoryStore()
        concurrency = AsyncConcurrencyManager()
        timeline = SacredTimeline(
            concurrency_manager=concurrency,
            memory_store=memory,
        )

        prompt = f"{context}\n\n{goal}".strip() if context else goal
        return await timeline.handle_user_input(prompt, thread_id=task_id)

    try:
        result = _run_sync(_execute())
        return {"status": "completed", "result": result, "task_id": task_id}
    except Exception as exc:
        logger.exception("run_agent_task[%s] failed", task_id)
        return {"status": "failed", "error": str(exc), "task_id": task_id}
