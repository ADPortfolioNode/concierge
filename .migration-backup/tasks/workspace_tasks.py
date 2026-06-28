"""Celery tasks for processing files uploaded via the workstation.

These tasks are enqueued by the jobs router when processing large/slow files
so the HTTP request returns immediately with a job_id for polling.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

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
        return asyncio.run(coro)


@celery_app.task(bind=True, name="tasks.workspace_tasks.process_uploaded_file")
def process_uploaded_file(
    self,
    upload_id: str,
    filename: str,
    task_type: str = "read_file",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process a previously-uploaded workstation file using a file agent.

    Args:
        upload_id: UUID assigned at upload time (used to locate the stored file).
        filename:  Original filename (used for type detection / display).
        task_type: Agent action — one of ``read_file``, ``dataset_analysis``,
                   ``generate_code``.  Defaults to ``"read_file"``.
        extra:     Optional additional payload forwarded to the agent.

    Returns:
        Dict with ``status``, ``result`` / ``error``, and ``task_id``.
    """
    task_id = self.request.id
    logger.info(
        "process_uploaded_file[%s] upload_id=%r filename=%r task_type=%r",
        task_id,
        upload_id,
        filename,
        task_type,
    )

    async def _execute():
        from agents.file_agents import (
            FileReaderAgent,
            FileEditorAgent,
            DatasetAnalysisAgent,
            CodeExecutionAgent,
        )

        payload: Dict[str, Any] = {
            "upload_id": upload_id,
            "filename": filename,
            **(extra or {}),
        }

        agent_map = {
            "read_file": FileReaderAgent,
            "dataset_analysis": DatasetAnalysisAgent,
            "generate_code": CodeExecutionAgent,
            "write_file": FileEditorAgent,
        }
        agent_cls = agent_map.get(task_type)
        if agent_cls is None:
            raise ValueError(f"Unknown task_type {task_type!r}")

        agent = agent_cls()
        # All file agents expose an async `run(payload)` coroutine.
        return await agent.run(payload)

    try:
        result = _run_sync(_execute())
        return {"status": "completed", "result": result, "task_id": task_id}
    except Exception as exc:
        logger.exception("process_uploaded_file[%s] failed", task_id)
        return {"status": "failed", "error": str(exc), "task_id": task_id}
