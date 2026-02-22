"""Async Vector Search Tool using `MemoryStore`.

This tool is a thin adapter that exposes an async `search` method returning
relevant memory summaries for a query string. It's designed to be used by
TaskAgents prior to execution to provide context (RAG pattern).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class VectorSearchTool:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top_k relevant memory entries for `query`.

        The returned entries are dicts with keys `id`, `summary`, and `metadata`.
        """
        try:
            results = await self.memory.query(context=query, top_k=top_k)
            logger.debug("VectorSearchTool found %d results for query", len(results))
            return results
        except Exception:
            logger.exception("VectorSearchTool.search failed")
            return []


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        ms = MemoryStore()
        await ms.store_summary("taskX", "Important result about cats", {"status": "complete"})
        tool = VectorSearchTool(ms)
        res = await tool.search("cats")
        print(res)

    asyncio.run(_demo())
