"""Scenario test: search, execute code, store and retrieve JSON.

Run with: .venv\Scripts\python tests\scenario_test.py
"""
from __future__ import annotations

import asyncio
import json
import logging

import sys
from pathlib import Path

# Ensure project root is on sys.path for local imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.web_search_tool import WebSearchTool
from tools.code_execution_tool import CodeExecutionTool
from tools.file_memory_tool import FileMemoryTool
from tools.tool_registry import register_tool, registry
from memory.memory_store import MemoryStore
from task_agent import TaskAgent

logging.basicConfig(level=logging.INFO)


class DummyLLM:
    async def generate(self, prompt: str, context: str | None = None) -> str:
        # Distinguish between router prompts (which ask for a single tool name)
        # and general assistant prompts (which should return a human-friendly result).
        prompt_text = (prompt or "").lower()
        ctx_text = (context or "").lower()

        # If the prompt looks like the ToolRouter prompt, return a tool name
        if "available tools" in prompt_text or "tool router" in prompt_text or "respond with only the tool name" in prompt_text:
            if "search" in ctx_text or "orchestration" in ctx_text or "find" in ctx_text:
                return "web_search"
            if "execute" in ctx_text or "run code" in ctx_text or "print(" in ctx_text or "python" in ctx_text:
                return "code_exec"
            if "store" in ctx_text or "save" in ctx_text or "configuration" in ctx_text or "json" in ctx_text:
                return "file_memory"
            return "none"

        # Otherwise act like a normal assistant producing a concise result
        # Prefer context if provided (TaskAgent passes context there when available)
        combined = (ctx_text + " " + prompt_text).strip()
        if "print(" in combined:
            # Simulate the result of printing range(5)
            return "Execution result: 0 1 2 3 4"
        if "orchestration" in combined or "async" in combined or "search" in combined:
            return "Found patterns: use asyncio tasks, queues, and supervisor loops for orchestration."
        if "configuration" in combined or "store" in combined:
            return "Configuration stored and available under provided key."
        # default friendly reply
        return "OK: processed instruction"


async def main():
    dummy = DummyLLM()

    # Memory with injected LLM for any compression/summarization
    memory = MemoryStore(collection_name="scenario_mem", llm_tool=dummy)
    # Force in-memory fallback to avoid attempting Chroma connections in local test
    memory._client = None
    memory._collection = None

    # Register tools
    register_tool(WebSearchTool())
    register_tool(CodeExecutionTool())
    register_tool(FileMemoryTool())

    # 1) Search async orchestration patterns
    t1 = {"task_id": "s1", "title": "Search async patterns", "instructions": "Search async orchestration patterns"}
    agent1 = TaskAgent(task_name="search-task", task_input=t1, memory=memory, vector_tool=None, llm_tool=dummy)
    r1 = await agent1.run()
    print("Search result:", r1.get("output"))

    # 2) Execute code: print(range(5))
    t2 = {"task_id": "c1", "title": "Run code", "instructions": "Execute code: print(range(5))"}
    agent2 = TaskAgent(task_name="code-task", task_input=t2, memory=memory, vector_tool=None, llm_tool=dummy)
    r2 = await agent2.run()
    print("Code exec result:", r2.get("output"))

    # 3) Store configuration JSON
    cfg = {"key": "cfg1", "value": {"timeout": 30, "retries": 3}}
    store_instr = f"STORE {json.dumps(cfg)}"
    # call FileMemoryTool directly for clarity
    fm = registry().get("file_memory")
    assert fm is not None
    out_store = await fm.run(store_instr)
    print("Store result:", out_store)

    # 4) Retrieve stored configuration
    out_get = await fm.run("GET cfg1")
    print("Retrieve result:", out_get)


if __name__ == "__main__":
    asyncio.run(main())
