"""FileReaderAgent — reads an uploaded file and returns its text content."""

from __future__ import annotations

import logging
from typing import Any

from tasks.task_model import Task
from ._sandbox import read_file_safe

logger = logging.getLogger(__name__)


class FileReaderAgent:
    """Reads files from the upload sandbox.

    Task payload expected keys:
        upload_id (str): UUID of the upload directory.
        filename (str): Name of the file to read.
    """

    name = "file_reader"
    description = "Reads an uploaded file and returns its text content."

    async def handle_task(self, task: Task) -> dict[str, Any]:
        upload_id: str = task.payload.get("upload_id", "")
        filename: str = task.payload.get("filename", "")

        if not upload_id or not filename:
            raise ValueError("Task payload must include 'upload_id' and 'filename'.")

        logger.info("FileReaderAgent reading %s/%s", upload_id, filename)
        text = read_file_safe(upload_id, filename)
        return {
            "type": "read_file",
            "upload_id": upload_id,
            "filename": filename,
            "content": text,
            "chars": len(text),
        }

    # Convenience alias so the agent can also be called directly.
    async def read_file(self, upload_id: str, filename: str) -> str:
        """Direct call interface (bypasses task queue)."""
        return read_file_safe(upload_id, filename)
