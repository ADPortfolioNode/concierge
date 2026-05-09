from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from memory.memory_store import MemoryStore
from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)


class BaseAgent:
    """Abstract base for specialized agents.

    Subclasses should implement `run_task` which accepts a task dict and
    returns a structured result (dict).
    """

    def __init__(
        self,
        name: str,
        memory: MemoryStore,
        llm: Optional[LLMTool] = None,
    ) -> None:
        self.name = name
        self.memory = memory
        self.llm = llm
        self._lock = asyncio.Lock()

    async def prepare(self) -> None:
        # hook for subclasses
        return None

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError()

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Public entrypoint for running tasks. Acquires per-agent lock to
        avoid concurrent runs in same agent instance.
        """
        # Guard: prevent accidental file-editing when the environment
        # explicitly disables it. This checks for common file-editing
        # intent phrases in the task instructions and returns a clear
        # error if edits are not allowed.
        allow_file_edits = os.environ.get("ALLOW_FILE_EDITS", "0").lower() in ("1", "true", "yes")
        text = task.get("instructions") or task.get("code") or ""
        if not allow_file_edits and isinstance(text, str):
            lowered = text.lower()
            triggers = ("write file", "create file", "edit file", "save file", "apply_patch", "apply_patch(", "open(")
            if any(k in lowered for k in triggers):
                return {"error": "file editing is disabled in this environment. Set ALLOW_FILE_EDITS=1 to enable in development.", "agent": self.name}
        async with self._lock:
            logger.info("%s executing task: %s", self.name, task.get("title") or task.get("task_id"))
            try:
                out = await self.run_task(task)
                # persist a memory note about completion
                try:
                    await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "task"), summary=str(out), metadata={"agent_type": self.name, "status": "complete"})
                except Exception:
                    logger.exception("Failed to store agent output in memory")
                return out
            except Exception as exc:
                logger.exception("Agent %s failed: %s", self.name, exc)
                return {"error": str(exc), "agent": self.name}
