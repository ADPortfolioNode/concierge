"""Facade to shared concurrency logic.

Orchestration modules previously imported this class directly from
``orchestration.concurrency``.  Moving the implementation into ``core``
namespaced package lets us share it widely, so this file now simply
re-exports from the new location.
"""

from __future__ import annotations

# re-export everything for backwards compatibility
from core.concurrency import *
    def __init__(self, max_agents: int = 3) -> None:
        self.max_agents = max_agents
        self._active: Dict[str, asyncio.Task] = {}
        # priority queue: list of tuples (-priority, counter, agent_id, coro, future)
        self._queue = []
        self._counter = 0
        self._lock = asyncio.Lock()
        # metrics
        self.peak = 0
        self.overlap_count = 0

    def active_count(self) -> int:
        return len(self._active)

    def can_spawn(self) -> bool:
        return self.active_count() < self.max_agents

    async def register(self, agent_coro: Awaitable[Any], priority: float = 0.0) -> Tuple[str, asyncio.Future]:
        agent_id = str(uuid.uuid4())
        result_future: asyncio.Future = asyncio.get_running_loop().create_future()

        async with self._lock:
            if self.can_spawn():
                task = asyncio.create_task(self._run_agent(agent_id, agent_coro, result_future))
                self._active[agent_id] = task
            else:
                # push onto heap with negative priority for max-heap behavior
                self._counter += 1
                import heapq
                heapq.heappush(self._queue, (-priority, self._counter, agent_id, agent_coro, result_future))

        return agent_id, result_future

    async def _run_agent(self, agent_id: str, agent_coro: Awaitable[Any], result_future: asyncio.Future) -> None:
        # update metrics
        cnt = self.active_count()
        if cnt > self.peak:
            self.peak = cnt
        if cnt > 1:
            self.overlap_count += 1
        try:
            result = await agent_coro
            if not result_future.cancelled():
                result_future.set_result(result)
        except Exception as exc:
            if not result_future.cancelled():
                result_future.set_exception(exc)
        finally:
            async with self._lock:
                self._active.pop(agent_id, None)
                await self._start_next_from_queue()

    async def _start_next_from_queue(self) -> None:
        if self.can_spawn() and self._queue:
            try:
                import heapq
                _, _, agent_id, agent_coro, result_future = heapq.heappop(self._queue)
            except Exception:
                return
            task = asyncio.create_task(self._run_agent(agent_id, agent_coro, result_future))
            self._active[agent_id] = task

    async def complete(self, agent_id: str) -> None:
        async with self._lock:
            task = self._active.pop(agent_id, None)
            if task and not task.done():
                task.cancel()
            await self._start_next_from_queue()

    def list_active(self) -> Dict[str, asyncio.Task]:
        return dict(self._active)

    def metrics(self) -> Dict[str, int]:
        return {"peak": self.peak, "overlap_count": self.overlap_count}


__all__ = ["AsyncConcurrencyManager"]
