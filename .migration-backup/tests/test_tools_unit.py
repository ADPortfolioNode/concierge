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
import httpx
import types

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

    # test LLMTool fallback when the primary key is rate-limited
    async def _test_llmtool_fallback():
        import tools.llm_tool as llm_module
        # dummy client that fails first request with 429 then succeeds
        class DummyResp:
            def __init__(self, status_code, lines):
                self.status_code = status_code
                self._lines = lines
            async def __aenter__(self):
                if self.status_code == 429:
                    raise httpx.HTTPStatusError("rate limit", request=None, response=self)
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise httpx.HTTPStatusError("status", request=None, response=self)
            async def aiter_lines(self):
                for line in self._lines:
                    yield line

        class DummyClient:
            def __init__(self):
                self.calls = []
            def stream(self, method, url, json, headers, timeout):
                self.calls.append(headers.get("Authorization"))
                # first call -> rate limit, second -> done
                if len(self.calls) == 1:
                    return DummyResp(429, [])
                return DummyResp(200, ["data: [DONE]"])

        # manually set environment and patch function
        os.environ["OPENAI_API_KEY"] = "primary"
        os.environ["OPENAI_API_KEYS"] = "fallback"
        llm_module._get_client = lambda: DummyClient()

        tool = llm_module.LLMTool()
        out = await tool.generate("hello")
        # on success output should not start with error prefix
        assert not out.startswith("[LLM-Error]")
        assert tool._api_keys == ["primary", "fallback"]
        # ensure the client used both keys in sequence
        assert llm_module._get_client().calls == ["Bearer primary", "Bearer fallback"]

    await _test_llmtool_fallback()

    # test Gemini fallback when no OpenAI keys available or they all fail
    async def _test_llmtool_gemini():
        import tools.llm_tool as llm_module
        os.environ["GEMINI_API_KEY"] = "gemkey"

        # case A: no OpenAI keys at all
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_API_KEYS", None)
        tool = llm_module.LLMTool()
        tool._call_gemini = lambda prompt, context: asyncio.sleep(0) or "gem-resp1"
        out = await tool.generate("hi there")
        assert out == "gem-resp1"

        # case B: OpenAI keys exist but both rate-limit, gemini is used
        os.environ["OPENAI_API_KEY"] = "primary"
        os.environ["OPENAI_API_KEYS"] = "secondary"
        # patch client to always give 429
        class DummyResp2:
            def __init__(self):
                pass
            async def __aenter__(self):
                raise httpx.HTTPStatusError("rate limit", request=None, response=types.SimpleNamespace(status_code=429))
            async def __aexit__(self, exc_type, exc, tb):
                pass
        class DummyClient2:
            def stream(self, *args, **kwargs):
                return DummyResp2()
        llm_module._get_client = lambda: DummyClient2()
        tool = llm_module.LLMTool()
        tool._call_gemini = lambda prompt, context: "gem-resp2"
        out2 = await tool.generate("another prompt")
        assert out2 == "gem-resp2"

    await _test_llmtool_gemini()

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
