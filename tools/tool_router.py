"""LLM-assisted tool selector (ToolRouter).

Given a task instruction and available tools, returns the selected tool name.
Falls back to heuristics if the LLM does not return a known tool.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .tool_registry import list_tools, get_tool, registry
from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)


class ToolRouter:
    """LLM-assisted tool selector (ToolRouter).

    Given a task instruction and available tools, returns the selected tool name.
    Falls back to heuristics if the LLM does not return a known tool. The prompt
    includes each tool's name and description to improve selection quality.
    """

    def __init__(self, llm: Optional[LLMTool] = None) -> None:
        self.llm = llm or LLMTool()

    async def select_tool(self, instruction: str, available_tools: Optional[List[str]] = None) -> Optional[str]:
        available_names = available_tools or list_tools()
        # build a richer available list with descriptions
        avail_with_desc = []
        for n in available_names:
            t = registry().get(n)
            desc = getattr(t, "description", "") if t else ""
            avail_with_desc.append(f"{n}: {desc}")

        prompt = (
            "You are a tool router assistant. Given the instruction and the list of available tools below, choose the single best tool name to accomplish the task.\n"
            f"Available tools:\n{chr(10).join(avail_with_desc)}\n\nInstruction:\n{instruction}\n\nRespond with only the tool name or 'none' if no tool is appropriate."
        )
        try:
            resp = await self.llm.generate(prompt, context=instruction)
            resp_text = (resp or "").strip().lower()
            # match exact tool name or substring
            for t in available_names:
                if resp_text == t.lower() or t.lower() in resp_text:
                    logger.info("ToolRouter selected via LLM: %s", t)
                    return t
        except Exception:
            logger.exception("ToolRouter LLM failed")

        # fallback heuristics
        inst = instruction.lower()
        if "search" in inst or "find" in inst or "web" in inst:
            return "web_search" if get_tool("web_search") else None
        if "run code" in inst or "execute" in inst or "python" in inst or "code" in inst:
            return "code_exec" if get_tool("code_exec") else None
        if "store" in inst or "save" in inst or "json" in inst or "file" in inst:
            return "file_memory" if get_tool("file_memory") else None

        return None
