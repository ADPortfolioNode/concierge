"""Registers default task handlers on the global queue.

Import and call :func:`register_default_handlers` once at startup.
"""

from __future__ import annotations

import logging

from .task_queue import get_queue

logger = logging.getLogger(__name__)


def register_default_handlers() -> None:
    """Wire up built-in file-agent handlers to the task queue."""
    from agents.file_agents.dataset_analysis_agent import DatasetAnalysisAgent
    from agents.file_agents.file_reader_agent import FileReaderAgent
    from agents.file_agents.file_editor_agent import FileEditorAgent
    from agents.file_agents.code_execution_agent import CodeExecutionAgent

    q = get_queue()

    reader = FileReaderAgent()
    editor = FileEditorAgent()
    executor = CodeExecutionAgent()
    analyst = DatasetAnalysisAgent()

    q.register_handler("read_file",        reader.handle_task)
    q.register_handler("write_file",       editor.handle_task)
    q.register_handler("append_file",      editor.handle_append_task)
    q.register_handler("generate_code",    executor.handle_task)
    q.register_handler("dataset_analysis", analyst.handle_task)

    logger.info("TaskWorker: default handlers registered.")
