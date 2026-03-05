"""Phase 9 adaptive intelligence tests.

Run with: python tests/phase9_tests.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

# ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore, IntelligenceNode
from config.settings import get_settings

logging.basicConfig(level=logging.DEBUG)

async def test_concurrency_priority_ordering():
    """Ensure AsyncConcurrencyManager respects priority values.

    We use max_agents=0 so all registrations are queued and we can inspect
    the internal heap ordering without race conditions.
    """
    cm = AsyncConcurrencyManager(max_agents=0)

    async def make_task(name):
        await asyncio.sleep(0.01)
        return name

    # schedule two tasks, low then high priority
    await cm.register(make_task("low"), priority=1.0)
    await cm.register(make_task("high"), priority=5.0)
    # inspect internal queue; highest priority should be first element
    import heapq
    # note stored as (-priority, counter, agent_id, coro, fut)
    first = cm._queue[0]
    assert first[0] == -5.0, f"expected highest priority in queue, got {first[0]}"
    # cancel queued futures and close coroutines so we don't leak warnings
    for entry in cm._queue:
        try:
            entry[4].cancel()
        except Exception:
            pass
        try:
            # entry[3] is the coroutine
            entry[3].close()
        except Exception:
            pass
    print("Concurrency priority ordering passed")

async def test_compute_priority_determinism():
    """Verify coordinator's priority computation is deterministic and uses explicit priority."""
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(), memory_store=MemoryStore())
    task = {"title": "Do work", "instructions": "some instructions"}
    ctx = {"prior_ids": []}
    p1 = coord._compute_priority(task, ctx)
    p2 = coord._compute_priority(task, ctx)
    assert p1 == p2, "priority computation not deterministic"
    # explicit priority multiplier
    task["priority"] = 2.0
    p3 = coord._compute_priority(task, ctx)
    assert p3 > p1, "explicit priority did not increase score"
    print("Compute priority determinism passed")

async def test_contradiction_detection_and_autotasks():
    """Populate memory with contradicting nodes and ensure detection + auto-task spawn."""
    ms = MemoryStore(collection_name="phase9_contra_test")
    # clear graph
    ms._graph.clear()
    # create two nodes with simple contradiction heuristic
    n1 = IntelligenceNode(id="n1", goal=None, summary="Cats are great", parent_ids=[], timestamp="", confidence=1.0)
    n1.key_points = ["cats"]
    n2 = IntelligenceNode(id="n2", goal=None, summary="Not cats are great", parent_ids=[], timestamp="", confidence=1.0)
    n2.key_points = ["cats"]
    # manually set contradiction risk since heuristic runs only on insert
    n2.contradiction_risk = 0.7
    ms._graph[n1.id] = n1
    ms._graph[n2.id] = n2
    # threshold lower than default to catch them
    contras = ms.get_contradiction_nodes(threshold=0.1)
    assert any(n.id == "n2" for n in contras), "contradiction node not detected"
    # now run coordinator to see auto task spawn
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(max_agents=1), memory_store=ms)
    # simple plan with no real tasks: we can monkeypatch planner to return empty tasks list
    class DummyPlanner:
        async def plan(self, goal):
            return {"tasks": []}
    coord._planner = DummyPlanner()
    res = await coord.run_autonomous("dummy goal", max_depth=1, max_tasks=5)
    tm = res.get("task_map") or {}
    auto_keys = [k for k in tm.keys() if k.startswith("auto_reconcile_")]
    assert auto_keys, "auto reconcile tasks were not spawned"
    print("Contradiction detection and auto-task spawn passed")

async def test_graph_pruning():
    """Nodes with confidence below threshold should be archived."""
    ms = MemoryStore(collection_name="phase9_prune_test")
    ms._graph.clear()
    low = IntelligenceNode(id="low", goal=None, summary="x", parent_ids=[], timestamp="", confidence=0.05)
    hi = IntelligenceNode(id="hi", goal=None, summary="y", parent_ids=[], timestamp="", confidence=0.9)
    ms._graph[low.id] = low
    ms._graph[hi.id] = hi
    ms.prune_graph(confidence_threshold=0.1)
    assert not ms._graph[low.id].active, "low confidence node not archived"
    assert ms._graph[hi.id].active, "high confidence node incorrectly archived"
    print("Graph pruning passed")

async def test_retrieval_bias_and_determinism():
    """Retrieval should favor higher-priority metadata and be deterministic."""
    ms = MemoryStore(collection_name="phase9_retrieval_test")
    ms._graph.clear()
    ms._index.clear()
    # add nodes with 'cats' token but different priority metadata
    node_a = IntelligenceNode(id="a", goal=None, summary="cats info", parent_ids=[], timestamp="", confidence=1.0)
    node_b = IntelligenceNode(id="b", goal=None, summary="cats info", parent_ids=[], timestamp="", confidence=1.0)
    ms._graph[node_a.id] = node_a
    ms._graph[node_b.id] = node_b
    for tok in set(node_a.summary.split()):
        if len(tok) > 3:
            ms._index.setdefault(tok, set()).add(node_a.id)
            ms._index.setdefault(tok, set()).add(node_b.id)
    # use priority metadata by manually constructing hit dicts
    # monkey patch query to return both with different priority
    async def fake_query(ctx, top_k=5):
        return [
            {"id": "a", "summary": "cats info", "metadata": {"priority": 0.5}},
            {"id": "b", "summary": "cats info", "metadata": {"priority": 2.0}},
        ]
    ms.query = fake_query  # type: ignore
    hits1 = await ms.retrieve_relevant_intelligence("cats")
    assert hits1 and hits1[0]["id"] == "b", f"expected b first, got {hits1}"
    hits2 = await ms.retrieve_relevant_intelligence("cats")
    assert hits1 == hits2, "retrieval order not deterministic"
    print("Retrieval bias and determinism passed")

async def run_all():
    await test_concurrency_priority_ordering()
    await test_compute_priority_determinism()
    await test_contradiction_detection_and_autotasks()
    await test_graph_pruning()
    await test_retrieval_bias_and_determinism()
    print("All Phase 9 tests passed")

if __name__ == "__main__":
    asyncio.run(run_all())
