"""Run async coroutines from sync code safely (including inside a running loop)."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")


def run_coro_sync(coro) -> T:
    """Complete *coro* from synchronous code.

    Uses ``asyncio.run`` when no loop is running; otherwise runs the coroutine
    in a worker thread with its own event loop (avoids nested ``asyncio.run``).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()