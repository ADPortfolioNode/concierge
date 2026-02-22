"""Async-capable base tool interface.

Tools should implement `run` (sync) or `arun` (async). Concrete tools
should also expose `name` and `description` properties.
"""

from __future__ import annotations

import asyncio
from typing import Protocol
import logging

logger = logging.getLogger(__name__)


class Tool(Protocol):
    """Protocol that concrete tools should follow."""

    name: str
    description: str

    async def run(self, input_data: str) -> str:
        ...


class BaseTool:
    """Base class for async-capable tools.

    Concrete tools should override `run` (async) or `arun` for backward
    compatibility. This base provides a default `run` implementation that
    echoes input and an `arun` wrapper for older call sites.
    """

    name = "base"
    description = "Base tool that echoes input."

    async def run(self, input_data: str) -> str:  # pragma: no cover - trivial
        return f"BaseTool echo: {input_data}"

    async def arun(self, input_data: str) -> str:
        # Backwards compatible wrapper for older tools using `arun` name
        try:
            return await self.run(input_data)
        except Exception as exc:
            logger.exception("BaseTool.arun failed: %s", exc)
            raise

    # older alias kept for compatibility
    async def run_async(self, input_data: str) -> str:
        return await self.arun(input_data)
