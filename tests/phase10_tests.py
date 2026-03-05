"""Phase 10 autonomy and cross-task orchestration tests.

Run with: python tests/phase10_tests.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore, IntelligenceNode

logging.basicConfig(level=logging.DEBUG)

async def test_critic_strictness():
    ms = MemoryStore(collection_name="phase10_critic_test")
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(), memory_store=ms)
    # fake planner that produces a single task with invalid output
    class DummyPlanner:
        async def plan(self, goal):
            return {"tasks": [{"task_id": "t1", "title": "Bad Output", "instructions": "Produce bad json", "depends_on": []}]}
    coord._planner = DummyPlanner()

    # monkeypatch CriticAgent to return unparsable string
    orig = coord._llm.generate
    async def bad_gen(prompt, context=None):
        return "not a json"
    coord._llm.generate = bad_gen  # type: ignore
    res = await coord.run_autonomous("anything", max_depth=1, max_tasks=5)
    crit = res.get("evaluation", {})
    assert crit.get("decision") == "refine", "Critic should refine on bad output"
    print("Critic strictness passed")
    coord._llm.generate = orig  # restore

async def test_cross_task_reuse_and_persistence():
    ms = MemoryStore(collection_name="phase10_reuse_test")
    ms._graph.clear(); ms._index.clear()
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(), memory_store=ms)

    # first run generates a task that stores some summary under known id
    class P1:
        async def plan(self, goal):
            return {"tasks": [{"task_id": "a", "title": "First", "instructions": "say hello", "depends_on": []}]}
    coord._planner = P1()
    res1 = await coord.run_autonomous("run1")
    # after run1 graph should contain node id 'a'
    assert "a" in ms._graph, "Node for task a should persist"
    # second run should reuse that graph entry in context
    class P2:
        async def plan(self, goal):
            return {"tasks": [{"task_id": "b", "title": "Second", "instructions": "refer to previous", "depends_on": []}]}
    coord._planner = P2()
    res2 = await coord.run_autonomous("run2")
    # ensure memory_hit in second result
    assert res2.get("memory_hit"), "Second run should hit memory"
    print("Cross-task reuse passed")

async def test_graph_state_updates():
    ms = MemoryStore(collection_name="phase10_state_test")
    ms._graph.clear(); ms._index.clear()
    # manually insert node with low confidence
    n = IntelligenceNode(id="x", goal=None, summary="old", parent_ids=[], timestamp="", confidence=0.2)
    ms._graph[n.id] = n
    # simulate storing same task again
    await ms.store_summary(task_name="whatever", summary="updated", metadata={"task_id": "x"})
    assert ms._graph["x"].summary == "updated", "Graph node should update summary"
    print("Graph state updates passed")

async def test_autonomous_conflict_prioritization():
    ms = MemoryStore(collection_name="phase10_conflict_test")
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(max_agents=2), memory_store=ms)
    # plan with two dependent tasks of differing priority
    class PC:
        async def plan(self, goal):
            return {"tasks": [
                {"task_id": "low", "title": "Low", "instructions": "", "priority": 1, "depends_on": []},
                {"task_id": "high", "title": "High", "instructions": "", "priority": 10, "depends_on": []},
            ]}
    coord._planner = PC()
    res = await coord.run_autonomous("conflict", max_depth=1, max_tasks=5)
    # ensure high started before low via ordering of logs
    # we can't easily inspect logs here, but we can verify evaluation order by timestamps in memory
    nodes = list(ms._graph.values())
    highs = [n for n in nodes if n.id == "high"]
    lows = [n for n in nodes if n.id == "low"]
    assert highs and lows, "both nodes present"
    # assume insertion order corresponds to execution order
    assert nodes.index(highs[0]) < nodes.index(lows[0]), "high-priority executed first"
    print("Autonomous conflict prioritization passed")

async def run_all():
    await test_critic_strictness()
    await test_cross_task_reuse_and_persistence()
    await test_graph_state_updates()
    await test_autonomous_conflict_prioritization()
    print("All Phase 10 tests passed")

if __name__ == "__main__":
    asyncio.run(run_all())
