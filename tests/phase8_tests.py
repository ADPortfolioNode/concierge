"""Phase 8 scalability and graph integrity tests.

Run with: python tests/phase8_tests.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import sys

# ensure project root on path when running tests directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore, IntelligenceNode

logging.basicConfig(level=logging.DEBUG)

async def test_concurrent_roots():
    """Launch multiple root goals concurrently and verify concurrency metrics."""
    ms = MemoryStore(collection_name="phase8_test")
    # clear any existing graph
    ms._graph.clear()
    ms._index.clear()
    goals = [f"Goal number {i} test" for i in range(5)]
    # use one shared concurrency manager so independent roots compete for slots
    shared_cm = AsyncConcurrencyManager(max_agents=3)
    coordinators = [SacredTimeline(concurrency_manager=shared_cm, memory_store=ms) for _ in goals]
    tasks = [c.run_autonomous(g, max_depth=1, max_tasks=5) for c,g in zip(coordinators, goals)]
    start = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start
    # check at least one manager saw overlapping execution
    peaks = [c._concurrency.peak for c in coordinators]
    overlaps = [c._concurrency.overlap_count for c in coordinators]
    assert any(p > 1 for p in peaks), f"expected concurrency peaks >1, got {peaks}"
    assert any(o > 0 for o in overlaps), f"expected some overlap count >0, got {overlaps}"
    print("Concurrent roots test passed, peaks", peaks, "overlaps", overlaps, "duration", duration)

async def test_memory_graph_integrity():
    """Validate graph structure: no cycles, all parent_ids exist."""
    ms = MemoryStore(collection_name="phase8_graph_test")
    # build a simple chain
    ms._graph.clear()
    ms._index.clear()
    # manually insert nodes a -> b -> c
    node_a = IntelligenceNode(id="a", goal=None, summary="A", parent_ids=[], timestamp="", confidence=1.0)
    node_b = IntelligenceNode(id="b", goal=None, summary="B", parent_ids=["a"], timestamp="", confidence=1.0)
    node_c = IntelligenceNode(id="c", goal=None, summary="C", parent_ids=["b"], timestamp="", confidence=1.0)
    for n in (node_a, node_b, node_c):
        ms._graph[n.id] = n
    # check no cycles: simple DFS
    visited = set()
    stack = set()
    def dfs(nid):
        if nid in stack:
            return False
        if nid in visited:
            return True
        visited.add(nid)
        stack.add(nid)
        for pid in ms._graph[nid].parent_ids:
            if pid not in ms._graph:
                raise AssertionError(f"Parent {pid} missing")
            if not dfs(pid):
                return False
        stack.remove(nid)
        return True
    assert dfs("c"), "cycle detected"
    print("Graph integrity test passed")

async def test_reflection_control():
    """Trigger low-confidence outputs to ensure reflection is bounded."""
    ms = MemoryStore(collection_name="phase8_reflect_test")
    coord = SacredTimeline(concurrency_manager=AsyncConcurrencyManager(max_agents=2), memory_store=ms)
    # craft a goal likely to score low (contains 'error' word)
    res = await coord.run_autonomous("produce output with error and bug", max_depth=2, max_tasks=5)
    # ensure that refine counts for tasks do not exceed limits
    for tid, t in (res.get("task_map") or {}).items():
        assert t.get("refine_count", 0) <= 2, "refine exceeded limit"
    print("Reflection control test passed")

async def test_load_stability():
    """Insert many nodes and assert retrieval time stays small."""
    ms = MemoryStore(collection_name="phase8_load_test")
    ms._graph.clear()
    ms._index.clear()
    # add 100 nodes
    for i in range(100):
        nid = f"node{i}"
        node = IntelligenceNode(id=nid, goal=None, summary=f"summary about cats {i}", parent_ids=[], timestamp="", confidence=1.0)
        ms._graph[nid] = node
        tokens = set(w.strip('.,').lower() for w in node.summary.split() if len(w) > 3)
        for tok in tokens:
            ms._index.setdefault(tok, set()).add(nid)
    # measure retrieval
    start = time.time()
    hits = await ms.retrieve_relevant_intelligence("cats")
    elapsed = time.time() - start
    assert elapsed < 0.5, f"retrieval too slow: {elapsed}"
    assert hits, "expected hits"
    print("Load stability test passed, retrieval", elapsed)

async def run_all():
    await test_concurrent_roots()
    await test_memory_graph_integrity()
    await test_reflection_control()
    await test_load_stability()
    print("All Phase 8 tests passed")

if __name__ == "__main__":
    asyncio.run(run_all())
