"""Simple unit-style tests for the tool ecosystem.

Run with: python tests/test_tools_unit.py

These are lightweight checks that don't require pytest.
"""
from __future__ import annotations

import sys
import asyncio
import logging
import os
import shutil

# ensure project root on path when running tests directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.file_memory_tool import FileMemoryTool
from tools.code_execution_tool import CodeExecutionTool
from tools.tool_router import ToolRouter
from tools.tool_registry import register_tool, registry
from tools.web_search_tool import WebSearchTool
from tools.llm_tool import LLMTool

logging.basicConfig(level=logging.DEBUG)


class DummyLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def generate(self, prompt: str, context: str | None = None) -> str:
        # respond with web_search for router tests
        if "choose the single best tool name" in (prompt or ""):
            return "web_search"
        return "ok"


async def _test_file_memory_tool(tmpdir: str):
    t = FileMemoryTool(base_dir=tmpdir)
    out = await t.run('STORE {"key":"u1","value":{"x":123}}')
    assert "STORED" in out
    out2 = await t.run('GET u1')
    assert "FOUND u1" in out2


async def _test_code_execution_tool():
    t = CodeExecutionTool()
    out = await t.arun('print(1+2)')
    if "3" not in out:
        print("CodeExecutionTool output:", repr(out))
    assert "3" in out
    bad = await t.arun('import os\nos.system("echo hi")')
    assert "ERROR" in bad or "unsafe" in bad


async def _test_tool_router():
    llm = DummyLLM()
    router = ToolRouter(llm=llm)
    register_tool(WebSearchTool())
    sel = await router.select_tool("Search for something", available_tools=registry().list_tools())
    assert sel == "web_search"


async def run_all():
    tmpdir = os.path.join(os.getcwd(), "tests_tmp")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    os.makedirs(tmpdir, exist_ok=True)

    await _test_file_memory_tool(tmpdir)
    await _test_code_execution_tool()
    await _test_tool_router()

    # memory retrieval deterministic behaviour
    async def _test_memory_retrieval():
        from memory.memory_store import MemoryStore
        ms = MemoryStore()
        # clear any preloaded entries
        ms._in_memory.clear()
        # store a couple of summaries with overlapping keywords
        await ms.store_summary("t1", "Findings about cats and dogs", {})
        await ms.store_summary("t2", "More research about cats", {})
        hits = await ms.retrieve_relevant_intelligence("cats")
        assert hits, "expected some memories for 'cats'"
        # deterministic order
        hits2 = await ms.retrieve_relevant_intelligence("cats")
        assert hits == hits2

    await _test_memory_retrieval()

    shutil.rmtree(tmpdir)
    print("All tool unit tests passed")


if __name__ == "__main__":
    asyncio.run(run_all())
