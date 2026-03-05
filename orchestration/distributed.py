"""Simplified distributed orchestration helpers for Phase 11.

This module simulates multiple nodes running their own SacredTimeline
instances while sharing a common MemoryStore and a global concurrency
limiter. The implementation is intentionally lightweight for testing and
ensures deterministic behavior by avoiding randomness and relying on
round-robin task assignment.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from orchestration.sacred_timeline import SacredTimeline

class GlobalConcurrencyManager:
    """Tracks active tasks across all nodes and enforces a global limit."""
    def __init__(self, max_global: int = 10):
        self.max_global = max_global
        self._active = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            if self._active < self.max_global:
                self._active += 1
                return True
            return False

    async def release(self) -> None:
        async with self._lock:
            self._active = max(0, self._active - 1)

    def active_count(self) -> int:
        return self._active

class NodeScheduler:
    """Distributes tasks among multiple node coordinators."""
    def __init__(self, nodes: List[SacredTimeline], global_cm: GlobalConcurrencyManager):
        self.nodes = nodes
        self.global_cm = global_cm
        self._next = 0
        self._lock = asyncio.Lock()

    async def schedule(self, coro):
        # round-robin assignment respecting global concurrency
        async with self._lock:
            node = self.nodes[self._next]
            self._next = (self._next + 1) % len(self.nodes)
        # wait until global slot available
        while not await self.global_cm.acquire():
            await asyncio.sleep(0.01)
        try:
            return await node._concurrency._run_agent(str(id(coro)), coro, asyncio.get_running_loop().create_future())
        finally:
            await self.global_cm.release()

# simple factory

def create_distributed_nodes(count: int, memory: Optional[MemoryStore] = None, max_global: int = 10) -> (List[SacredTimeline], GlobalConcurrencyManager):
    """Create multiple SacredTimeline nodes sharing memory."""
    memory = memory or MemoryStore(collection_name="distributed")
    global_cm = GlobalConcurrencyManager(max_global=max_global)
    nodes = []
    for i in range(count):
        cm = AsyncConcurrencyManager(max_agents=3)
        node = SacredTimeline(concurrency_manager=cm, memory_store=memory)
        nodes.append(node)
    return nodes, global_cm
