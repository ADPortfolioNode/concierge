from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    def __init__(self, memory, llm: Optional[LLMTool] = None):
        super().__init__(name="CriticAgent", memory=memory, llm=llm)

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        outputs = task.get("outputs") or task.get("output") or {}
        prompt = (
            f"Evaluate the following outputs for quality, correctness, and completeness: {outputs}\n"
            "Provide a JSON object with keys: decision (approve|refine), score (0-100), comments, suggestions (list)."
        )

        if self.llm is None:
            return {
                "agent": self.name,
                "decision": "approve",
                "score": 80,
                "comments": "No LLM available; heuristic approve.",
                "suggestions": [],
            }

        try:
            resp = await self.llm.generate(prompt, context=str(outputs))
        except Exception:
            logger.exception("Critic LLM failed")
            return {"agent": self.name, "decision": "refine", "score": 50, "comments": "LLM error", "suggestions": []}

        try:
            parsed = json.loads(resp)
        except Exception:
            parsed = {"agent": self.name, "decision": "refine", "score": 50, "comments": resp, "suggestions": []}

        parsed.setdefault("agent", self.name)

        # persist critic feedback
        try:
            await self.memory.store_summary(
                task_name=task.get("title") or task.get("task_id", "critic"),
                summary=str(parsed),
                metadata={"agent_type": self.name, "decision": parsed.get("decision")},
            )
        except Exception:
            logger.exception("Failed to store critic feedback in memory")

        return parsed
