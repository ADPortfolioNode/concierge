"""Async concurrency manager for scheduling TaskAgent coroutines.

Enforces a maximum number of concurrently running agents and queues
additional agent coroutines. Exposes `register` to schedule a coroutine
and returns `(agent_id, future)` where the future resolves with the
coroutine's result.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Dict, Tuple


class AsyncConcurrencyManager:
    def __init__(self, max_agents: int = 3) -> None:
        self.max_agents = max_agents
        self._active: Dict[str, asyncio.Task] = {}
        self._queue: asyncio.Queue[Tuple[str, Awaitable[Any], asyncio.Future]] = asyncio.Queue()
        self._lock = asyncio.Lock()

    def active_count(self) -> int:
        return len(self._active)

    def can_spawn(self) -> bool:
        return self.active_count() < self.max_agents

    async def register(self, agent_coro: Awaitable[Any]) -> Tuple[str, asyncio.Future]:
        agent_id = str(uuid.uuid4())
        result_future: asyncio.Future = asyncio.get_running_loop().create_future()

        async with self._lock:
            if self.can_spawn():
                task = asyncio.create_task(self._run_agent(agent_id, agent_coro, result_future))
                self._active[agent_id] = task
            else:
                await self._queue.put((agent_id, agent_coro, result_future))

        return agent_id, result_future

    async def _run_agent(self, agent_id: str, agent_coro: Awaitable[Any], result_future: asyncio.Future) -> None:
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
        if self.can_spawn() and not self._queue.empty():
            try:
                agent_id, agent_coro, result_future = self._queue.get_nowait()
            except asyncio.QueueEmpty:
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


__all__ = ["AsyncConcurrencyManager"]