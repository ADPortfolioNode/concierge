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
        instructions = task.get("instructions") or task.get("code") or ""
        goal = task.get("goal") or instructions

        if not instructions:
            return {"agent": self.name, "error": "no instructions provided"}

        # Generate code from natural-language instructions using LLM
        code = instructions
        if self.llm is not None:
            try:
                prompt = (
                    f"Write concise, working code to accomplish the following task.\n"
                    f"Return ONLY the code with no markdown fences or extra explanation.\n\n"
                    f"Task: {instructions}"
                )
                generated = await self.llm.generate(prompt, context=goal)
                if generated and generated.strip():
                    code = generated.strip()
            except Exception:
                logger.exception("CodingAgent LLM code generation failed")

        # Attempt sandboxed execution; gracefully handle failures without poisoning output
        exec_result = ""
        if code:
            try:
                exec_out = await self.exec_tool.arun(code)
                if exec_out and not exec_out.startswith("ERROR:"):
                    exec_result = exec_out
            except Exception:
                logger.exception("CodingAgent code execution failed")

        result_text = code
        if exec_result:
            result_text = f"{code}\n\n# Output:\n{exec_result}"

        return {"agent": self.name, "code": code, "output": result_text, "exec_result": exec_result}
