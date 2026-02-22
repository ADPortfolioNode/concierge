from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from tools.code_execution_tool import CodeExecutionTool

logger = logging.getLogger(__name__)


class CodingAgent(BaseAgent):
    def __init__(self, memory, llm: Optional[object] = None):
        super().__init__(name="CodingAgent", memory=memory, llm=llm)
        self.exec_tool = CodeExecutionTool()

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        code = task.get("instructions") or task.get("code") or ""
        if not code:
            return {"agent": self.name, "error": "no code provided"}

        # run code using execution tool
        try:
            out = await self.exec_tool.arun(code)
        except Exception as exc:
            logger.exception("CodeExecution failed")
            return {"agent": self.name, "error": str(exc)}

        # structured result
        return {"agent": self.name, "code": code, "output": out}
