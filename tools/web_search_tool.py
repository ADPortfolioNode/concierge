"""Mock async web search tool.

This is a deterministic mock used for testing and development.
"""

from __future__ import annotations

import asyncio
from .base_tool import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Mock web search that returns deterministic results."

    async def arun(self, input_data: str) -> str:
        # Simulate network latency
        await asyncio.sleep(0.1)
        query = input_data.strip()
        return f"[WebSearchTool] Results for '{query}': (mocked summary)"
