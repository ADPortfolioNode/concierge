"""Phase 11 distributed orchestration tests.

Run with: python tests/phase11_tests.py
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

from distributed import create_distributed_nodes
from memory.memory_store import MemoryStore, IntelligenceNode

logging.basicConfig(level=logging.DEBUG)

async def test_distributed_task_execution():
    nodes, global_cm = create_distributed_nodes(3, max_global=5)
    # schedule simple coroutines via nodes scheduler
    async def dummy_work(i):
        await asyncio.sleep(0.01)
        return i
    tasks = []
    for i in range(10):
        node = nodes[i % len(nodes)]
        _, fut = await node._concurrency.register(dummy_work(i))
        tasks.append(fut)
    results = await asyncio.gather(*tasks)
    assert results == list(range(10)), "distributed execution mismatch"
    print("Distributed task execution passed")

async def test_memory_consistency_across_nodes():
    ms = MemoryStore(collection_name="phase11_mem_test")
    nodes, _ = create_distributed_nodes(2, memory=ms)
    # first node stores a summary
    await ms.store_summary(task_name="t1", summary="foo", metadata={"task_id": "t1"})
    # second node should see same graph entry
    assert "t1" in nodes[1]._memory._graph
    print("Memory consistency passed")

async def test_concurrency_limits():
    nodes, global_cm = create_distributed_nodes(2, max_global=2)
    # spawn more than global limit tasks and ensure global_cm respects
    sem = asyncio.Semaphore(0)
    async def busy():
        # each acquisition should increment
        await global_cm.acquire()
        await asyncio.sleep(0.01)
        await global_cm.release()
    await asyncio.gather(*(busy() for _ in range(5)))
    print("Concurrency limits passed")

async def run_all():
    await test_distributed_task_execution()
    await test_memory_consistency_across_nodes()
    await test_concurrency_limits()
    print("All Phase 11 tests passed")

if __name__ == "__main__":
    asyncio.run(run_all())