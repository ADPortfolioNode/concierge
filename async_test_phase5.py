"""Phase 5 autonomous execution test.

Run with: python async_test_phase5.py

This script uses a DummyLLM to deterministically simulate planning,
task execution, and evaluation. It prints the generated plan, each task
result, evaluator decision, and final reflection stored in memory.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from tools.vector_search_tool import VectorSearchTool

import agents.planner as planner_mod
import agents.evaluator as evaluator_mod
import task_agent as task_agent_mod
import tools.llm_tool as llm_mod
from orchestration.sacred_timeline import SacredTimeline


logging.basicConfig(level=logging.INFO)


class DummyLLM:
    """Deterministic async mock LLM.

    - For planning prompts, returns a JSON array of two tasks.
    - For evaluator prompts, returns 'complete'.
    - For task prompts, returns a short result string.
    """

    def __init__(self, *args, **kwargs):
        pass

    async def generate(self, prompt: str, context: Any = None) -> str:
        p = (prompt or "").lower()
        # Planner prompt detection
        if "break the following user goal" in p:
            tasks = [
                {
                    "task_id": "t1",
                    "title": "Survey architectures",
                    "instructions": "Search literature and summarize common AI orchestration architectures.",
                    "depends_on": [],
                },
                {
                    "task_id": "t2",
                    "title": "Collect best practices",
                    "instructions": "List best practices for designing orchestrations (reliability, observability, idempotency).",
                    "depends_on": ["t1"],
                },
            ]
            return json.dumps(tasks)

        # Evaluator prompt detection
        if "you are an evaluator" in p or "decision:" in p:
            # Deterministically say complete so the loop finishes
            return "complete"

        # Task execution: return a short deterministic summary
        if "provide a concise result" in p or "provide a concise result." in p:
            ctx = context or "no-context"
            return f"[DummyLLM] concise result; context={ctx}"

        # Fallback
        return "ok"


async def main():
    goal = "Research AI orchestration architectures and summarize best practices."

    # Monkeypatch LLM classes in modules so Planner, Evaluator, and TaskAgent
    # use DummyLLM.
    llm_mod.LLMTool = DummyLLM
    planner_mod.LLMTool = DummyLLM
    evaluator_mod.LLMTool = DummyLLM
    task_agent_mod.LLMTool = DummyLLM

    # Create core components
    # Inject DummyLLM into MemoryStore to enable compression code paths and
    # set a low threshold so we can exercise compression in the test.
    dummy_llm = DummyLLM()
    memory = MemoryStore(collection_name="phase5_test_memory", llm_tool=dummy_llm, compress_threshold=5)
    vector = VectorSearchTool(memory)
    concurrency = AsyncConcurrencyManager(max_agents=3)

    # Create planner instance (will use DummyLLM)
    planner = planner_mod.Planner()

    # Show generated plan
    plan = await planner.plan(goal)
    print("Generated plan:")
    print(json.dumps(plan, indent=2))

    # Create SacredTimeline with injected planner and run autonomous loop
    timeline = SacredTimeline(concurrency_manager=concurrency, memory_store=memory, planner=planner, vector_tool=vector)

    print("\nStarting autonomous run...\n")
    result = await timeline.run_autonomous(goal, max_depth=3, max_tasks=10, per_task_timeout=30)

    print("Autonomous run result:")
    print(json.dumps(result, indent=2))

    # Print task outputs (task_map) if present
    task_map = result.get("task_map", {})
    if task_map:
        print("\nTask results:")
        for tid, info in task_map.items():
            print(f"- {tid}: status={info.get('status')}, output={info.get('output')}")

    # Print evaluator decision if present
    eval_decision = result.get("evaluation")
    if eval_decision:
        print("\nEvaluator decision:")
        print(eval_decision)

    # Confirm memory entries persisted
    print("\nMemory entries (in-memory fallback):")
    mem_entries = getattr(memory, "_in_memory", [])
    print(f"Total entries: {len(mem_entries)}")
    # Show reflection entries
    reflections = [e for e in mem_entries if e.get("metadata", {}).get("task_name") == "reflection"]
    print(f"Reflections stored: {len(reflections)}")
    for r in reflections:
        print(r)

    # Exercise compression explicitly: add several extra summaries to exceed
    # the low threshold and run compression synchronously for the test.
    print("\nAdding extra entries to trigger compression...")
    for i in range(8):
        await memory.store_summary(f"task_extra_{i}", f"This is extra summary {i}", {"note": "extra"})

    print(f"Entries before explicit compression: {len(getattr(memory, '_in_memory', []))}")
    comp_id = await memory.compress_old_memories(force=True, keep_recent=3)
    print(f"Compression result id: {comp_id}")
    print(f"Entries after compression: {len(getattr(memory, '_in_memory', []))}")
    for e in getattr(memory, '_in_memory', []):
        print(f"- {e['id']} archived={e.get('metadata', {}).get('archived', False)}")


if __name__ == "__main__":
    asyncio.run(main())
