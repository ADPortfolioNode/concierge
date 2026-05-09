"""Phase 4 integration test for concierge.

This script performs a minimal async integration test that exercises:
- Vector search context retrieval
- Dummy LLM generation
- Async TaskAgent execution under AsyncConcurrencyManager
- Storing LLM-generated outputs in MemoryStore

Run with: `python phase4_test.py`
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
import tools.llm_tool as llm_module
from tools.vector_search_tool import VectorSearchTool


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("phase4_test")


class DummyLLM:
    """Deterministic async dummy LLM for local testing.

    The `generate` method simulates reasoning by returning a clearly
    identifiable string including the prompt and an abbreviated context.
    """

    def __init__(self, model: str = "dummy-model", timeout: int = 5) -> None:
        self.model = model
        self.timeout = timeout

    async def generate(self, prompt: str, context: str | None = None) -> str:
        await asyncio.sleep(0.05)  # simulate small latency
        ctx = (context[:200] + "...") if context and len(context) > 200 else (context or "(no context)")
        return f"[DummyLLM:{self.model}] Prompt: {prompt} | Context: {ctx}"


async def main() -> None:
    logger.info("Starting Phase 4 test")

    # Monkeypatch the real LLMTool to use DummyLLM so TaskAgents instantiate it
    llm_module.LLMTool = DummyLLM

    # Create core components
    memory = MemoryStore(collection_name="phase4_test_memory")
    vector_tool = VectorSearchTool(memory)
    concurrency = AsyncConcurrencyManager(max_agents=3)

    # Create SacredTimeline with injected components
    timeline = SacredTimeline(concurrency_manager=concurrency, memory_store=memory, vector_tool=vector_tool)

    # Trigger the planner to return multiple tasks by including the word 'batch'
    user_input = "Please process this batch of items and summarize results"

    logger.info("Submitting request to SacredTimeline: %s", user_input)
    result = await timeline.handle_user_input(user_input)

    logger.info("SacredTimeline returned: %s", result)

    # Print LLM-enhanced outputs
    if isinstance(result, dict) and result.get("status", "") in ("spawned_multiple", "spawned"):
        results = result.get("results") or [result]
        print("\nLLM-enhanced agent outputs:")
        for r in results:
            # r is the dict returned by _track_agent
            res = r.get("result") if isinstance(r, dict) else None
            out = res.get("output") if res else None
            print("-", out)

    # Inspect memory store contents for verification
    print("\nStored memory entries:")
    # Use internal in-memory list when Chroma isn't configured
    in_memory = getattr(memory, "_in_memory", None)
    if in_memory is not None:
        for rec in in_memory:
            print(f"- id={rec.get('id')} task={rec.get('metadata', {}).get('task_name')} summary={rec.get('summary')}")
    else:
        # Attempt queries for each task name found in result
        if isinstance(result, dict):
            results = result.get("results") or [result]
            for r in results:
                task_name = r.get("result", {}).get("agent_id")
                q = await memory.query(task_name or "", top_k=10)
                for item in q:
                    print(f"- {item}")

    logger.info("Phase 4 test complete")


if __name__ == "__main__":
    asyncio.run(main())
