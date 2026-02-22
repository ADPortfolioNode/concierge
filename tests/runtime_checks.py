"""Runtime checks for ToolRouter, CodeExecutionTool, and concurrency.

Run with: .venv\Scripts\python tests\runtime_checks.py
"""
from __future__ import annotations

import asyncio
import logging
import json
import os

from tools.tool_router import ToolRouter
from tools.tool_registry import register_tool, registry
from tools.web_search_tool import WebSearchTool
from tools.code_execution_tool import CodeExecutionTool
from tools.file_memory_tool import FileMemoryTool
from task_agent import TaskAgent
from memory.memory_store import MemoryStore
from tools.llm_tool import LLMTool
from concurrency import AsyncConcurrencyManager

logging.basicConfig(level=logging.INFO)


class DummyLLM:
    async def generate(self, prompt: str, context: str | None = None) -> str:
        p = (prompt or "").lower()
        if "choose the single best tool name" in p or "respond with only the tool name" in p:
            return "web_search"
        if "provide a concise result" in p:
            return "[dummy] concise"
        return "ok"


async def test_toolrouter():
    print("\n== ToolRouter Tests ==")
    llm = DummyLLM()
    # register web_search and code_exec
    register_tool(WebSearchTool())
    register_tool(CodeExecutionTool())
    tr = ToolRouter(llm=llm)

    sel = await tr.select_tool("Search for recent papers about orchestration", available_tools=registry().list_tools())
    print("Selected tool (search):", sel)

    # heuristic: code
    sel2 = await tr.select_tool("Run python code to compute 2+2", available_tools=registry().list_tools())
    print("Selected tool (code heuristic):", sel2)


async def test_code_exec():
    print("\n== CodeExecutionTool Tests ==")
    t = CodeExecutionTool()

    out = await t.arun('print(1+2)')
    print("print(1+2) ->", repr(out))

    out2 = await t.arun('import os\nprint(2)')
    print("import os ->", repr(out2))

    out3 = await t.arun('for i in range(3): print(i)')
    print("loop ->", repr(out3))


async def test_concurrency_race(n_agents: int = 10):
    print("\n== Concurrency Stress Test ==")
    mem = MemoryStore(collection_name="runtime_check_mem")
    # use DummyLLM everywhere
    dummy = DummyLLM()
    # tools
    register_tool(WebSearchTool())
    register_tool(FileMemoryTool())
    # create concurrency manager
    cm = AsyncConcurrencyManager(max_agents=5)

    agents = []
    for i in range(n_agents):
        task = {"task_id": f"t{i}", "title": f"task{i}", "instructions": "Search something"}
        a = TaskAgent(task_name=f"task-{i}", task_input=task, memory=mem, vector_tool=None, llm_tool=dummy)
        agents.append(a)

    # spawn all
    coros = [a.run() for a in agents]

    # use gather to run concurrently but limit concurrency via AsyncConcurrencyManager inside SacredTimeline normally
    results = await asyncio.gather(*coros, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    print(f"Ran {n_agents} agents; errors: {len(errors)}")

    # check memory entries
    entries = getattr(mem, "_in_memory", [])
    print(f"Memory entries after run: {len(entries)}")


async def main():
    await test_toolrouter()
    await test_code_exec()
    await test_concurrency_race(12)


if __name__ == "__main__":
    asyncio.run(main())
