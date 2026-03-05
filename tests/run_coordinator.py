"""Run the Coordinator (`SacredTimeline`) with a DummyLLM to test Critic loops.

Two modes are executed:
- approve: Critic approves immediately
- refine: Critic always requests refine (tests max_refine enforcement)

Run with: .venv\Scripts\python tests\run_coordinator.py
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import sys
from pathlib import Path

# ensure project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestration.sacred_timeline import SacredTimeline
from memory.memory_store import MemoryStore
from agents.planner import Planner


class DummyLLM:
    def __init__(self, mode: str = "approve"):
        self.mode = mode

    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        p = (prompt or "").lower()
        ctx = (context or "").lower()
        # Planner prompt detection
        if "break the following user goal" in p:
            # return a simple JSON plan: search then code
            plan = [
                {"task_id": "t1", "title": "Survey web", "instructions": "Search async orchestration patterns"},
                {"task_id": "t2", "title": "Write example", "instructions": "Execute code: print(list(range(5)))", "depends_on": ["t1"]},
            ]
            return json.dumps(plan)

        # ToolRouter prompt detection
        if "respond with only the tool name" in p or "available tools" in p:
            if "search" in ctx or "orchestration" in ctx:
                return "web_search"
            if "execute" in ctx or "print(" in ctx or "code" in ctx:
                return "code_exec"
            return "none"

        # Critic evaluation prompt
        if "evaluate the following outputs" in p or "provide a json object" in p:
            if self.mode == "approve":
                return json.dumps({"decision": "approve", "score": 90, "comments": "Looks good", "suggestions": []})
            else:
                return json.dumps({"decision": "refine", "score": 40, "comments": "Needs more detail", "suggestions": ["Expand example"]})

        # Default assistant reply
        if "print(list(range(5))" in ctx or "print(range(5))" in ctx:
            return "Execution result: 0 1 2 3 4"
        if "async orchestration" in ctx or "orchestration" in ctx:
            return "Found patterns: use asyncio tasks, queues, supervisors"
        return "OK"


async def run_one(mode: str):
    print(f"\n=== Running coordinator with Critic mode: {mode} ===")
    llm = DummyLLM(mode=mode)
    ms = MemoryStore(collection_name="coord_test_collection", llm_tool=llm)
    # build a Planner that uses the DummyLLM so planning uses predictable plan
    planner = Planner(llm=llm)
    # create Coordinator with injected planner and override its shared llm
    coordinator = SacredTimeline(memory_store=ms, planner=planner)
    coordinator._llm = llm
    coordinator._memory._llm = llm
    coordinator._planner._llm = llm

    res = await coordinator.run_autonomous("Research async orchestration and write example implementation.", max_depth=3, max_tasks=10)
    print("Result:", res)


if __name__ == "__main__":
    asyncio.run(run_one("approve"))
    asyncio.run(run_one("refine"))
