"""Tool registry for registering and discovering tools."""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .base_tool import BaseTool


class ToolRegistry:
    """Thread-safe singleton-style registry for tools.

    This registry is safe to use from async code and from multiple threads.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._lock = threading.RLock()

    def register(self, tool: BaseTool) -> None:
        with self._lock:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> List[str]:
        with self._lock:
            return list(self._tools.keys())


# singleton registry
_REG = ToolRegistry()


def register_tool(tool: BaseTool) -> None:
    _REG.register(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    return _REG.get(name)


def list_tools() -> List[str]:
    return _REG.list_tools()


def registry() -> ToolRegistry:
    return _REG
