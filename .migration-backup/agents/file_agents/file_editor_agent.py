"""FileEditorAgent — writes or appends text to an uploaded file."""

from __future__ import annotations

import logging
from typing import Any

from tasks.task_model import Task
from ._sandbox import write_file_safe, append_file_safe

logger = logging.getLogger(__name__)


class FileEditorAgent:
    """Writes or appends content to files in the upload sandbox.

    write_file payload:
        upload_id (str), filename (str), content (str)

    append_file payload:
        upload_id (str), filename (str), content (str)
    """

    name = "file_editor"
    description = "Writes or appends content to uploaded files."

    # ------------------------------------------------------------------ #
    # write                                                                 #
    # ------------------------------------------------------------------ #

    async def handle_task(self, task: Task) -> dict[str, Any]:
        """Handle 'write_file' task type (overwrite)."""
        upload_id: str = task.payload.get("upload_id", "")
        filename: str = task.payload.get("filename", "")
        content: str = task.payload.get("content", "")

        if not upload_id or not filename:
            raise ValueError("Task payload must include 'upload_id' and 'filename'.")

        logger.info("FileEditorAgent writing %s/%s (%d chars)", upload_id, filename, len(content))
        write_file_safe(upload_id, filename, content)
        return {
            "type": "write_file",
            "upload_id": upload_id,
            "filename": filename,
            "bytes_written": len(content.encode()),
        }

    # ------------------------------------------------------------------ #
    # append                                                                #
    # ------------------------------------------------------------------ #

    async def handle_append_task(self, task: Task) -> dict[str, Any]:
        """Handle 'append_file' task type (non-destructive append)."""
        upload_id: str = task.payload.get("upload_id", "")
        filename: str = task.payload.get("filename", "")
        content: str = task.payload.get("content", "")

        if not upload_id or not filename:
            raise ValueError("Task payload must include 'upload_id' and 'filename'.")

        logger.info("FileEditorAgent appending %s/%s (%d chars)", upload_id, filename, len(content))
        append_file_safe(upload_id, filename, content)
        return {
            "type": "append_file",
            "upload_id": upload_id,
            "filename": filename,
            "bytes_appended": len(content.encode()),
        }
