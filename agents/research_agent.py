from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from tools.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    def __init__(self, memory, llm: Optional[object] = None):
        super().__init__(name="ResearchAgent", memory=memory, llm=llm)
        self.search_tool = WebSearchTool()

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("instructions") or task.get("query") or task.get("title") or "research"
        # use search tool
        try:
            results = await self.search_tool.arun(query)
        except Exception:
            logger.exception("WebSearchTool failed")
            results = ""

        # summarize using LLM if available
        summary = results
        if self.llm is not None:
            try:
                prompt = f"Summarize findings for: {query}\nResults:\n{results}"
                summary = await self.llm.generate(prompt, context=results)
            except Exception:
                logger.exception("LLM summarization failed")

        return {"agent": self.name, "query": query, "summary": summary}
